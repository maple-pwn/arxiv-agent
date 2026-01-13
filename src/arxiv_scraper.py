"""
ArXiv 论文抓取模块
提供论文搜索、数据保存等核心功能
"""

import arxiv
import hashlib
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from .ai_service import create_ai_service
from .markdown_generator import MarkdownGenerator
from .utils import (
    send_email_with_retry,
    send_report_via_webhook,
    format_paper_summary,
    create_retry_session
)


class ArxivScraper:
    """ArXiv 论文抓取器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化抓取器

        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.arxiv_config = config.get('arxiv', {})
        self.storage_config = config.get('storage', {})

        # 确保数据目录存在
        self.data_dir = self.storage_config.get('data_dir', './data/papers')
        self.pdf_dir = self.storage_config.get('pdf_dir', './data/pdfs')
        os.makedirs(self.data_dir, exist_ok=True)
        if self.storage_config.get('download_pdf', False):
            os.makedirs(self.pdf_dir, exist_ok=True)

        self.http_session = create_retry_session()

        self.cache_enabled = bool(self.storage_config.get('cache_enabled', True))
        self.cache_file = self.storage_config.get(
            'cache_file',
            os.path.join(self.data_dir, 'cache.json')
        )
        try:
            self.cache_max_items = int(self.storage_config.get('cache_max_items', 5000))
        except (TypeError, ValueError):
            self.cache_max_items = 5000
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_dirty = False
        self.ai_cache_key = self._build_ai_cache_key()
        self.filter_cache_key = self._build_filter_cache_key()
        if self.cache_enabled:
            self._load_cache()

    def build_query(self) -> str:
        """
        构建 ArXiv 查询字符串

        Returns:
            查询字符串
        """
        keywords = self.arxiv_config.get('keywords', [])
        categories = self.arxiv_config.get('categories', [])

        query_parts = []

        # 添加关键词查询
        if keywords:
            keyword_query = ' OR '.join([f'all:"{kw}"' for kw in keywords])
            query_parts.append(f'({keyword_query})')

        # 添加分类查询
        if categories:
            category_query = ' OR '.join([f'cat:{cat}' for cat in categories])
            query_parts.append(f'({category_query})')

        # 组合查询
        if query_parts:
            query = ' AND '.join(query_parts)
        else:
            query = 'all:*'  # 默认查询所有

        self.logger.debug(f"构建的查询字符串: {query}")
        return query

    def search_papers(self) -> List[Dict[str, Any]]:
        """
        搜索 ArXiv 论文

        Returns:
            论文列表
        """
        query = self.build_query()
        max_results = self.arxiv_config.get('max_results', 50)
        sort_by = self._get_sort_criterion()
        sort_order = self._get_sort_order()

        self.logger.info(f"开始搜索论文，最大结果数: {max_results}")

        try:
            # 创建搜索客户端
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )

            # 获取结果
            papers = []
            for result in search.results():
                paper_data = self._extract_paper_data(result)
                papers.append(paper_data)

            self.logger.info(f"成功获取 {len(papers)} 篇论文")

            # 去重（按 arxiv_id）
            papers = self._deduplicate_papers(papers)

            # 计算相关度评分
            papers = self._calculate_relevance_scores(papers)

            # 应用多级排序（如果配置了）
            papers = self._apply_multi_level_sort(papers)

            return papers

        except Exception as e:
            self.logger.error(f"搜索论文时出错: {str(e)}")
            raise

    def _calculate_relevance_scores(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        计算论文相关度评分

        基于用户搜索关键词，为每篇论文计算相关度评分（0.0-1.0）

        Args:
            papers: 论文列表

        Returns:
            添加了相关度评分的论文列表
        """
        keywords = self.arxiv_config.get('keywords', [])
        enable_relevance = self.arxiv_config.get('enable_relevance_score', True)

        if not enable_relevance or not keywords:
            self.logger.debug("相关度评分未启用或无关键词，跳过")
            for paper in papers:
                paper['relevance_score'] = 1.0  # 默认满分
            return papers

        self.logger.info(f"开始计算论文相关度评分（基于 {len(keywords)} 个关键词）...")

        for paper in papers:
            try:
                # 提取论文文本
                title = paper.get('title', '').lower()
                summary = paper.get('summary', '').lower()
                categories = ' '.join(paper.get('categories', [])).lower()

                # 计算匹配分数
                total_score = 0.0
                max_score = 0.0

                for keyword in keywords:
                    keyword_lower = keyword.lower()

                    # 标题匹配（权重: 5.0）
                    if keyword_lower in title:
                        total_score += 5.0
                    max_score += 5.0

                    # 摘要匹配（权重: 3.0）
                    # 计算关键词在摘要中出现的次数
                    summary_count = summary.count(keyword_lower)
                    if summary_count > 0:
                        # 出现次数越多分数越高，但有上限
                        total_score += min(summary_count * 0.5, 3.0)
                    max_score += 3.0

                    # 分类匹配（权重: 2.0）
                    if keyword_lower in categories:
                        total_score += 2.0
                    max_score += 2.0

                # 归一化到 0.0-1.0
                if max_score > 0:
                    relevance_score = min(total_score / max_score, 1.0)
                else:
                    relevance_score = 0.0

                paper['relevance_score'] = round(relevance_score, 3)

            except Exception as e:
                self.logger.warning(f"计算相关度评分失败 ({paper.get('arxiv_id', 'unknown')}): {str(e)}")
                paper['relevance_score'] = 0.5  # 默认中等评分

        # 统计评分分布
        scores = [p['relevance_score'] for p in papers]
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            self.logger.info(
                f"相关度评分完成 - 平均: {avg_score:.3f}, 最高: {max_score:.3f}, 最低: {min_score:.3f}"
            )

        return papers

    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按 arxiv_id 去重

        Args:
            papers: 论文列表

        Returns:
            去重后的论文列表
        """
        seen = set()
        unique_papers = []

        for paper in papers:
            arxiv_id = paper.get('arxiv_id')
            if not arxiv_id:
                unique_papers.append(paper)
                continue

            if arxiv_id in seen:
                continue

            seen.add(arxiv_id)
            unique_papers.append(paper)

        if len(unique_papers) != len(papers):
            self.logger.info(f"去重完成：{len(papers)} → {len(unique_papers)} 篇论文")

        return unique_papers

    def _get_max_workers(self, ai_config: Dict[str, Any], total_tasks: int) -> int:
        """根据配置和任务量获取并发数"""
        try:
            requested = int(ai_config.get('max_workers', 4))
        except (TypeError, ValueError):
            requested = 4

        if requested < 1:
            requested = 1

        if total_tasks <= 0:
            return 1

        return min(requested, total_tasks)

    def _get_cache_key(self, paper: Dict[str, Any]) -> Optional[str]:
        """获取缓存键"""
        arxiv_id = paper.get('arxiv_id')
        updated = paper.get('updated')
        if not arxiv_id or not updated:
            return None
        return f"{arxiv_id}:{updated}"

    def _get_cache_entry(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取缓存条目"""
        cache_key = self._get_cache_key(paper)
        if not cache_key:
            return None
        return self.cache.get(cache_key)

    def _get_prompts_signature(self) -> str:
        """获取 prompts 配置签名，用于缓存失效判断"""
        prompts_path = self.config.get('ai', {}).get('prompts_file', './prompts/prompts.yaml')
        try:
            import yaml
            with open(prompts_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 只计算关键 prompt 的哈希，忽略格式调整和注释
            relevant_prompts = {
                'summarize': data.get('summarize') if isinstance(data, dict) else None,
                'translate': data.get('translate') if isinstance(data, dict) else None,
                'insights': data.get('insights') if isinstance(data, dict) else None,
                'filter': data.get('filter') if isinstance(data, dict) else None
            }
            serialized = json.dumps(relevant_prompts, sort_keys=True, ensure_ascii=True)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        except FileNotFoundError:
            return "default"
        except Exception as e:
            self.logger.warning(f"读取 prompts 文件失败: {str(e)}")
            return "unknown"

    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        """生成稳定的配置哈希"""
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def _build_ai_cache_key(self) -> str:
        """构建 AI 处理缓存键"""
        ai_config = self.config.get('ai', {})
        provider = ai_config.get('provider', 'openai').lower()
        provider_key = 'anthropic' if provider in ['anthropic', 'claude'] else provider
        provider_config = ai_config.get(provider_key, {})

        payload = {
            'provider': provider_key,
            'model': provider_config.get('model'),
            'base_url': provider_config.get('base_url'),
            'max_tokens': provider_config.get('max_tokens'),
            'temperature': provider_config.get('temperature'),
            'prompts_signature': self._get_prompts_signature()
        }
        return self._hash_payload(payload)

    def _build_filter_cache_key(self) -> str:
        """构建筛选缓存键"""
        ai_config = self.config.get('ai', {})
        provider = ai_config.get('provider', 'openai').lower()
        provider_key = 'anthropic' if provider in ['anthropic', 'claude'] else provider
        provider_config = ai_config.get(provider_key, {})

        payload = {
            'provider': provider_key,
            'model': provider_config.get('model'),
            'base_url': provider_config.get('base_url'),
            'filter_keywords': ai_config.get('filter_keywords', '').strip(),
            'prompts_signature': self._get_prompts_signature()
        }
        return self._hash_payload(payload)

    def _load_cache(self) -> None:
        """加载缓存文件"""
        if not self.cache_file or not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict) and 'items' in data:
                self.cache = data.get('items', {})
            elif isinstance(data, dict):
                self.cache = data
            else:
                self.cache = {}

            self.logger.info(f"已加载缓存: {len(self.cache)} 条")

        except Exception as e:
            self.logger.warning(f"加载缓存失败: {str(e)}")
            self.cache = {}

    def _prune_cache(self) -> None:
        """裁剪缓存大小"""
        if not self.cache_max_items or len(self.cache) <= self.cache_max_items:
            return

        items = sorted(
            self.cache.items(),
            key=lambda item: item[1].get('cached_at', ''),
            reverse=True
        )
        self.cache = dict(items[:self.cache_max_items])
        self.logger.info(f"缓存已裁剪到 {self.cache_max_items} 条")

    def _save_cache(self) -> None:
        """保存缓存到磁盘"""
        if not self.cache_enabled or not self.cache_dirty:
            return

        try:
            self._prune_cache()
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)

            payload = {
                'version': 1,
                'items': self.cache
            }

            temp_path = f"{self.cache_file}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.cache_file)
            self.cache_dirty = False
            self.logger.info(f"缓存已保存: {self.cache_file}")

        except Exception as e:
            self.logger.warning(f"保存缓存失败: {str(e)}")

    def _update_cache_entry(
        self,
        paper: Dict[str, Any],
        ai_summary: Optional[Dict[str, Any]] = None,
        translation: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
        filter_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新缓存条目"""
        if not self.cache_enabled:
            return

        cache_key = self._get_cache_key(paper)
        if not cache_key:
            return

        entry = self.cache.get(cache_key, {})
        entry['cached_at'] = datetime.now().isoformat()

        if ai_summary is not None:
            entry['ai_cache_key'] = self.ai_cache_key
            entry['ai_summary'] = ai_summary
        if translation is not None:
            entry['ai_cache_key'] = self.ai_cache_key
            entry['translation'] = translation
        if insights is not None:
            entry['ai_cache_key'] = self.ai_cache_key
            entry['insights'] = insights
        if filter_result is not None:
            entry['filter_cache_key'] = self.filter_cache_key
            entry['filter_result'] = filter_result

        self.cache[cache_key] = entry
        self.cache_dirty = True

    def _apply_multi_level_sort(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        应用多级排序

        Args:
            papers: 论文列表

        Returns:
            排序后的论文列表
        """
        # 获取多级排序配置
        multi_sort = self.arxiv_config.get('multi_level_sort', [])

        if not multi_sort or not isinstance(multi_sort, list):
            self.logger.debug("未配置多级排序，使用默认排序")
            return papers

        self.logger.info(f"应用多级排序: {len(multi_sort)} 个排序条件")

        # 定义排序字段映射
        def get_sort_key(paper: Dict[str, Any], field: str):
            """获取论文的排序键值"""
            if field == 'submittedDate' or field == 'published':
                return paper.get('published', '')
            elif field == 'lastUpdatedDate' or field == 'updated':
                return paper.get('updated', '')
            elif field == 'relevance_score':
                # 相关度评分（如果有）
                return paper.get('relevance_score', 0.0)
            elif field == 'title':
                return paper.get('title', '')
            else:
                return ''

        # 构建排序键函数（支持多级排序）
        # Python sorted是稳定排序，所以需要反向遍历排序条件
        for sort_config in reversed(multi_sort):
            field = sort_config.get('field', 'submittedDate')
            order = sort_config.get('order', 'descending')

            reverse = (order == 'descending')

            try:
                papers = sorted(
                    papers,
                    key=lambda p: get_sort_key(p, field),
                    reverse=reverse
                )
                self.logger.debug(f"按 {field} ({order}) 排序完成")
            except Exception as e:
                self.logger.warning(f"排序失败 (字段: {field}): {str(e)}")

        return papers

    def _get_sort_criterion(self) -> arxiv.SortCriterion:
        """获取排序标准"""
        sort_by = self.arxiv_config.get('sort_by', 'submittedDate')
        sort_map = {
            'submittedDate': arxiv.SortCriterion.SubmittedDate,
            'lastUpdatedDate': arxiv.SortCriterion.LastUpdatedDate,
            'relevance': arxiv.SortCriterion.Relevance
        }
        return sort_map.get(sort_by, arxiv.SortCriterion.SubmittedDate)

    def _get_sort_order(self) -> arxiv.SortOrder:
        """获取排序顺序"""
        sort_order = self.arxiv_config.get('sort_order', 'descending')
        order_map = {
            'descending': arxiv.SortOrder.Descending,
            'ascending': arxiv.SortOrder.Ascending
        }
        return order_map.get(sort_order, arxiv.SortOrder.Descending)

    def _extract_paper_data(self, result: arxiv.Result) -> Dict[str, Any]:
        """
        从 ArXiv 结果中提取论文数据

        Args:
            result: ArXiv 搜索结果

        Returns:
            论文数据字典
        """
        return {
            'arxiv_id': result.entry_id.split('/')[-1],
            'title': result.title,
            'authors': [author.name for author in result.authors],
            'summary': result.summary,
            'published': result.published.isoformat(),
            'updated': result.updated.isoformat(),
            'categories': result.categories,
            'primary_category': result.primary_category,
            'pdf_url': result.pdf_url,
            'comment': result.comment,
            'journal_ref': result.journal_ref,
            'doi': result.doi,
            'links': [link.href for link in result.links]
        }

    def save_papers(self, papers: List[Dict[str, Any]]) -> List[str]:
        """
        保存论文数据

        Args:
            papers: 论文列表

        Returns:
            保存的文件路径列表
        """
        if not papers:
            self.logger.warning("没有论文需要保存")
            return []

        saved_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_format = self.storage_config.get('format', 'both')

        # 保存为 JSON
        if save_format in ['json', 'both']:
            json_file = self._save_as_json(papers, timestamp)
            if json_file:
                saved_files.append(json_file)

        # 保存为 CSV
        if save_format in ['csv', 'both']:
            csv_file = self._save_as_csv(papers, timestamp)
            if csv_file:
                saved_files.append(csv_file)

        # 下载 PDF（如果配置启用）
        if self.storage_config.get('download_pdf', False):
            self._download_pdfs(papers)

        return saved_files

    def _save_as_json(self, papers: List[Dict[str, Any]], timestamp: str) -> Optional[str]:
        """保存为 JSON 格式，返回文件路径"""
        filename = f"papers_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 JSON 文件: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存 JSON 文件时出错: {str(e)}")
            return None

    def _save_as_csv(self, papers: List[Dict[str, Any]], timestamp: str) -> Optional[str]:
        """保存为 CSV 格式，返回文件路径"""
        filename = f"papers_{timestamp}.csv"
        filepath = os.path.join(self.data_dir, filename)

        try:
            # 处理列表类型的字段
            df_data = []
            for paper in papers:
                paper_copy = paper.copy()
                paper_copy['authors'] = '; '.join(paper_copy['authors'])
                paper_copy['categories'] = '; '.join(paper_copy['categories'])
                paper_copy['links'] = '; '.join(paper_copy['links'])
                df_data.append(paper_copy)

            df = pd.DataFrame(df_data)
            df.to_csv(filepath, index=False, encoding='utf-8')
            self.logger.info(f"已保存 CSV 文件: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存 CSV 文件时出错: {str(e)}")
            return None

    def _download_pdfs(self, papers: List[Dict[str, Any]]) -> None:
        """
        下载论文 PDF

        Args:
            papers: 论文列表
        """
        self.logger.info(f"开始下载 {len(papers)} 篇论文的 PDF")

        for i, paper in enumerate(papers, 1):
            try:
                arxiv_id = paper['arxiv_id']
                pdf_url = paper['pdf_url']
                filename = f"{arxiv_id.replace('/', '_')}.pdf"
                filepath = os.path.join(self.pdf_dir, filename)

                # 如果文件已存在，跳过
                if os.path.exists(filepath):
                    self.logger.debug(f"PDF 已存在，跳过: {filename}")
                    continue

                # 下载 PDF（流式写入）
                response = self.http_session.get(pdf_url, timeout=30, stream=True)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                self.logger.info(f"[{i}/{len(papers)}] 已下载 PDF: {filename}")

            except Exception as e:
                self.logger.error(f"下载 PDF 失败 ({paper['arxiv_id']}): {str(e)}")

    def filter_papers_with_ai(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用 AI 筛选论文

        Args:
            papers: 论文列表

        Returns:
            筛选后的论文列表
        """
        ai_config = self.config.get('ai', {})

        if not ai_config.get('enable_filter', False):
            self.logger.debug("AI 筛选未启用，跳过")
            return papers

        filter_keywords = ai_config.get('filter_keywords', '').strip()
        if not filter_keywords:
            self.logger.warning("AI 筛选已启用，但未配置筛选关键词，跳过筛选")
            return papers

        filter_threshold = float(ai_config.get('filter_threshold', 0.7))

        # 创建 AI 服务
        ai_service = create_ai_service(ai_config)
        if not ai_service:
            self.logger.warning("AI 服务创建失败，跳过筛选")
            return papers

        self.logger.info(f"开始 AI 智能筛选论文（关键词：{filter_keywords}，阈值：{filter_threshold}）...")

        cached_hits = 0
        papers_to_filter = []
        for paper in papers:
            cache_entry = self._get_cache_entry(paper)
            cached_filter = None
            if cache_entry and cache_entry.get('filter_cache_key') == self.filter_cache_key:
                cached_filter = cache_entry.get('filter_result')

            if cached_filter:
                paper['filter_result'] = cached_filter
                cached_hits += 1
            else:
                papers_to_filter.append(paper)

        if cached_hits:
            self.logger.info(f"筛选缓存命中: {cached_hits} 篇论文")

        if papers_to_filter:
            max_workers = self._get_max_workers(ai_config, len(papers_to_filter))
            self.logger.info(f"并发筛选: {max_workers} 线程")

            if max_workers == 1:
                for i, paper in enumerate(papers_to_filter, 1):
                    try:
                        self.logger.info(f"[{i}/{len(papers_to_filter)}] 筛选: {paper['title'][:50]}...")
                        filter_result = ai_service.filter_paper(paper, filter_keywords)
                    except Exception as e:
                        self.logger.error(f"筛选失败 ({paper.get('arxiv_id', 'unknown')}): {str(e)}")
                        filter_result = {
                            'relevant': True,
                            'confidence': 0.5,
                            'reason': f'筛选失败: {str(e)}',
                            'status': 'error'
                        }

                    paper['filter_result'] = filter_result
                    if filter_result.get('status') == 'success':
                        self._update_cache_entry(paper, filter_result=filter_result)
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_paper = {
                        executor.submit(ai_service.filter_paper, paper, filter_keywords): paper
                        for paper in papers_to_filter
                    }

                    for future in as_completed(future_to_paper):
                        paper = future_to_paper[future]
                        try:
                            filter_result = future.result()
                        except Exception as e:
                            self.logger.error(
                                f"筛选失败 ({paper.get('arxiv_id', 'unknown')}): {str(e)}"
                            )
                            filter_result = {
                                'relevant': True,
                                'confidence': 0.5,
                                'reason': f'筛选失败: {str(e)}',
                                'status': 'error'
                            }

                        paper['filter_result'] = filter_result
                        if filter_result.get('status') == 'success':
                            self._update_cache_entry(paper, filter_result=filter_result)

        filtered_papers = []
        for paper in papers:
            filter_result = paper.get('filter_result')
            if not filter_result:
                filtered_papers.append(paper)
                continue

            if filter_result.get('relevant', False) and filter_result.get('confidence', 0.0) >= filter_threshold:
                filtered_papers.append(paper)

        self.logger.info(f"AI 筛选完成：{len(papers)} → {len(filtered_papers)} 篇论文")
        return filtered_papers

    def process_with_ai(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用 AI 处理论文（总结和翻译）

        Args:
            papers: 论文列表

        Returns:
            处理后的论文列表
        """
        ai_config = self.config.get('ai', {})

        if not ai_config.get('enabled', False):
            self.logger.debug("AI 功能未启用，跳过")
            return papers

        # 创建 AI 服务
        ai_service = create_ai_service(ai_config)
        if not ai_service:
            self.logger.warning("AI 服务创建失败，跳过 AI 处理")
            return papers

        enable_summary = ai_config.get('enable_summary', True)
        enable_translation = ai_config.get('enable_translation', True)
        enable_insights = ai_config.get('enable_insights', True)

        self.logger.info("开始 AI 处理论文...")

        cached_summary = 0
        cached_translation = 0
        cached_insights = 0
        tasks = []

        for paper in papers:
            cache_entry = self._get_cache_entry(paper)
            cache_valid = cache_entry and cache_entry.get('ai_cache_key') == self.ai_cache_key

            needs_summary = enable_summary
            if enable_summary and cache_valid:
                cached = cache_entry.get('ai_summary')
                if cached and cached.get('status') == 'success':
                    paper['ai_summary'] = cached
                    cached_summary += 1
                    needs_summary = False

            needs_translation = enable_translation and paper.get('summary')
            if enable_translation and cache_valid:
                cached = cache_entry.get('translation')
                if cached and not str(cached).startswith('翻译失败'):
                    paper['translation'] = cached
                    cached_translation += 1
                    needs_translation = False

            needs_insights = enable_insights
            if enable_insights and cache_valid:
                cached = cache_entry.get('insights')
                if cached and cached.get('status') == 'success':
                    paper['insights'] = cached
                    cached_insights += 1
                    needs_insights = False

            if needs_summary or needs_translation or needs_insights:
                tasks.append((paper, needs_summary, needs_translation, needs_insights))

        if cached_summary or cached_translation or cached_insights:
            self.logger.info(
                f"AI 缓存命中: 总结 {cached_summary}，翻译 {cached_translation}，洞察 {cached_insights}"
            )

        def process_single(task):
            paper, do_summary, do_translation, do_insights = task
            result = {}
            if do_summary:
                result['ai_summary'] = ai_service.summarize_paper(paper)
            if do_translation:
                result['translation'] = ai_service.translate_text(paper.get('summary', ''))
            if do_insights:
                result['insights'] = ai_service.extract_insights(paper)
            return paper, result

        if tasks:
            max_workers = self._get_max_workers(ai_config, len(tasks))
            if max_workers == 1:
                for i, task in enumerate(tasks, 1):
                    paper = task[0]
                    try:
                        self.logger.info(f"[{i}/{len(tasks)}] 处理: {paper['title'][:50]}...")
                        _, result = process_single(task)
                    except Exception as e:
                        self.logger.error(f"AI 处理失败 ({paper.get('arxiv_id', 'unknown')}): {str(e)}")
                        result = {}
                        if task[1]:
                            result['ai_summary'] = {
                                'summary': f"处理失败: {str(e)}",
                                'status': 'error'
                            }
                        if task[2]:
                            result['translation'] = f"翻译失败: {str(e)}"
                        if task[3]:
                            result['insights'] = {
                                'insights': [],
                                'status': 'error',
                                'error': str(e)
                            }

                    for key, value in result.items():
                        paper[key] = value

                    if result.get('ai_summary', {}).get('status') == 'success':
                        self._update_cache_entry(paper, ai_summary=result['ai_summary'])
                    if 'translation' in result and not str(result['translation']).startswith('翻译失败'):
                        self._update_cache_entry(paper, translation=result['translation'])
                    if result.get('insights', {}).get('status') == 'success':
                        self._update_cache_entry(paper, insights=result['insights'])
            else:
                self.logger.info(f"并发处理: {max_workers} 线程")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_task = {executor.submit(process_single, task): task for task in tasks}

                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        paper = task[0]
                        try:
                            _, result = future.result()
                        except Exception as e:
                            self.logger.error(
                                f"AI 处理失败 ({paper.get('arxiv_id', 'unknown')}): {str(e)}"
                            )
                            result = {}
                            if task[1]:
                                result['ai_summary'] = {
                                    'summary': f"处理失败: {str(e)}",
                                    'status': 'error'
                                }
                            if task[2]:
                                result['translation'] = f"翻译失败: {str(e)}"
                            if task[3]:
                                result['insights'] = {
                                    'insights': [],
                                    'status': 'error',
                                    'error': str(e)
                                }

                        for key, value in result.items():
                            paper[key] = value

                        if result.get('ai_summary', {}).get('status') == 'success':
                            self._update_cache_entry(paper, ai_summary=result['ai_summary'])
                        if 'translation' in result and not str(result['translation']).startswith('翻译失败'):
                            self._update_cache_entry(paper, translation=result['translation'])
                        if result.get('insights', {}).get('status') == 'success':
                            self._update_cache_entry(paper, insights=result['insights'])

        self.logger.info("AI 处理完成")
        return papers

    def generate_and_send_markdown_report(
        self,
        papers: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        生成 Markdown 报告并发送邮件

        Args:
            papers: 论文列表（已包含 AI 处理结果）

        Returns:
            Markdown 文件路径，如果失败则返回 None
        """
        ai_config = self.config.get('ai', {})

        if not ai_config.get('send_markdown_report', False):
            self.logger.debug("Markdown 报告发送未启用")
            return None

        try:
            # 创建 Markdown 生成器
            generator = MarkdownGenerator()

            # 生成 Markdown 内容
            self.logger.info("生成 Markdown 报告...")
            include_ai_summary = ai_config.get('enable_summary', True)
            include_translation = ai_config.get('enable_translation', True)
            include_insights = ai_config.get('enable_insights', True)

            markdown_content = generator.generate_paper_summary(
                papers,
                include_ai_summary=include_ai_summary,
                include_translation=include_translation,
                include_insights=include_insights
            )

            # 保存 Markdown 文件
            markdown_dir = ai_config.get('markdown_dir', './data/reports')
            os.makedirs(markdown_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arxiv_report_{timestamp}.md"
            filepath = os.path.join(markdown_dir, filename)

            if generator.save_to_file(markdown_content, filepath):
                self.logger.info(f"Markdown 报告已保存: {filepath}")

                # 发送报告
                notification_config = self.config.get('notification', {})
                if notification_config.get('enabled', False):
                    method = notification_config.get('method')
                    success = False

                    if method == 'email':
                        # 使用带重试机制的邮件发送
                        self.logger.info("发送 Markdown 报告到邮箱...")

                        message = f"""您好！

这是 ArXiv 论文日报，包含 {len(papers)} 篇论文的总结和翻译。

详情请查看附件中的 Markdown 文档。

---
自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

                        attachments = [{
                            'file_path': filepath,
                            'filename': filename
                        }]

                        email_config = notification_config.get('email', {})
                        # 使用重试机制，最多重试3次，每次间隔5秒
                        success = send_email_with_retry(
                            email_config,
                            message,
                            f"ArXiv 论文日报 - {datetime.now().strftime('%Y-%m-%d')}",
                            attachments,
                            max_retries=3,
                            retry_delay=5
                        )

                    elif method == 'webhook':
                        # 使用 Webhook 发送报告内容
                        self.logger.info("通过 Webhook 发送 Markdown 报告...")
                        webhook_config = notification_config.get('webhook', {})
                        success = send_report_via_webhook(
                            webhook_config,
                            markdown_content,
                            len(papers),
                            timestamp
                        )

                    else:
                        self.logger.warning(f"不支持的通知方式: {method}")

                    if success:
                        self.logger.info("Markdown 报告发送成功")

                        # 报告发送成功后，如果启用了自动清理，删除本地文件
                        if self.storage_config.get('auto_cleanup', False):
                            try:
                                os.remove(filepath)
                                self.logger.info(f"已删除本地 Markdown 文件: {filepath}")
                                return None  # 文件已删除，返回 None
                            except Exception as e:
                                self.logger.error(f"删除 Markdown 文件失败: {str(e)}")
                    else:
                        self.logger.warning("Markdown 报告发送失败，文件保留在本地")

                return filepath

        except Exception as e:
            self.logger.error(f"生成或发送 Markdown 报告失败: {str(e)}")
            return None

    def run(self) -> Dict[str, Any]:
        """
        执行一次完整的抓取流程

        Returns:
            执行结果
        """
        saved_paper_files = []
        papers: List[Dict[str, Any]] = []

        try:
            self.logger.info("=" * 50)
            self.logger.info("开始执行 ArXiv 论文抓取任务")
            self.logger.info("=" * 50)

            # 搜索论文
            papers = self.search_papers()

            # AI 智能筛选（在处理前过滤不相关论文）
            if papers:
                papers = self.filter_papers_with_ai(papers)

            # AI 处理（总结和翻译）
            if papers:
                papers = self.process_with_ai(papers)

            # 保存论文（包含 AI 处理结果）
            if papers:
                saved_paper_files = self.save_papers(papers)

            # 生成并发送 Markdown 报告
            markdown_path = None
            email_sent = False
            if papers:
                markdown_path = self.generate_and_send_markdown_report(papers)
                # 如果 markdown_path 为 None，说明邮件发送成功且已删除
                # 如果 markdown_path 不为 None，说明未发送或发送失败
                email_sent = (markdown_path is None and
                            self.config.get('ai', {}).get('send_markdown_report', False))

            # 如果启用了自动清理且邮件发送成功，删除 paper 文件
            if self.storage_config.get('auto_cleanup', False) and email_sent:
                for file_path in saved_paper_files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            self.logger.info(f"已删除本地论文文件: {file_path}")
                    except Exception as e:
                        self.logger.error(f"删除论文文件失败 ({file_path}): {str(e)}")

            result = {
                'success': True,
                'paper_count': len(papers),
                'markdown_report': markdown_path,
                'paper_summary': format_paper_summary(papers),
                'timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"任务执行成功，共抓取 {len(papers)} 篇论文")
            self.logger.info("=" * 50)

            return result

        except Exception as e:
            self.logger.error(f"任务执行失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            self._save_cache()
