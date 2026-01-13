"""
ArXiv 论文抓取模块
提供论文搜索、数据保存等核心功能
"""

import arxiv
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import requests

from .ai_service import create_ai_service, BaseAIService
from .markdown_generator import MarkdownGenerator
from .utils import send_email_with_retry, send_report_via_webhook


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

                # 下载 PDF
                response = requests.get(pdf_url, timeout=30)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(response.content)

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

        filtered_papers = []
        for i, paper in enumerate(papers, 1):
            try:
                self.logger.info(f"[{i}/{len(papers)}] 筛选: {paper['title'][:50]}...")

                # 调用 AI 筛选
                filter_result = ai_service.filter_paper(paper, filter_keywords)

                # 保存筛选结果
                paper['filter_result'] = filter_result

                # 根据相关性和置信度决定是否保留
                if filter_result.get('relevant', False) and filter_result.get('confidence', 0.0) >= filter_threshold:
                    filtered_papers.append(paper)
                    self.logger.info(
                        f"  ✓ 保留 (置信度: {filter_result.get('confidence', 0.0):.2f}, "
                        f"理由: {filter_result.get('reason', 'N/A')[:50]})"
                    )
                else:
                    self.logger.info(
                        f"  ✗ 过滤 (置信度: {filter_result.get('confidence', 0.0):.2f}, "
                        f"理由: {filter_result.get('reason', 'N/A')[:50]})"
                    )

            except Exception as e:
                self.logger.error(f"筛选失败 ({paper['arxiv_id']}): {str(e)}")
                # 出错时保留论文（保守策略）
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

        for i, paper in enumerate(papers, 1):
            try:
                self.logger.info(f"[{i}/{len(papers)}] 处理: {paper['title'][:50]}...")

                # AI 总结
                if enable_summary:
                    summary_result = ai_service.summarize_paper(paper)
                    paper['ai_summary'] = summary_result
                    self.logger.debug(f"总结状态: {summary_result.get('status')}")

                # 翻译摘要
                if enable_translation and paper.get('summary'):
                    translation = ai_service.translate_text(paper['summary'])
                    paper['translation'] = translation
                    self.logger.debug("翻译完成")

                # 提取关键洞察
                if enable_insights:
                    insights_result = ai_service.extract_insights(paper)
                    paper['insights'] = insights_result
                    self.logger.debug(f"洞察提取状态: {insights_result.get('status')}")

            except Exception as e:
                self.logger.error(f"AI 处理失败 ({paper['arxiv_id']}): {str(e)}")
                # 添加错误信息，但继续处理其他论文
                if enable_summary:
                    paper['ai_summary'] = {
                        'summary': f"处理失败: {str(e)}",
                        'status': 'error'
                    }
                if enable_translation:
                    paper['translation'] = f"翻译失败: {str(e)}"

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
