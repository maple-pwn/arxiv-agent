"""
Markdown 生成模块
将论文数据和 AI 总结生成格式化的 Markdown 文档
"""

import logging
from typing import List, Dict, Any
from datetime import datetime


class MarkdownGenerator:
    """Markdown 文档生成器"""

    def __init__(self):
        """初始化生成器"""
        self.logger = logging.getLogger(__name__)

    def generate_paper_summary(
        self,
        papers: List[Dict[str, Any]],
        include_ai_summary: bool = True,
        include_translation: bool = True,
        include_insights: bool = True
    ) -> str:
        """
        生成论文总结的 Markdown 文档

        Args:
            papers: 论文列表（包含 AI 总结和翻译）
            include_ai_summary: 是否包含 AI 总结
            include_translation: 是否包含翻译

        Returns:
            Markdown 格式的文档内容
        """
        lines = []

        # 标题
        lines.append("# ArXiv 论文日报")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**论文数量**: {len(papers)} 篇")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 目录
        lines.append("## 目录")
        lines.append("")
        for i, paper in enumerate(papers, 1):
            title = paper.get('title', 'N/A')
            # 清理标题中的特殊字符
            title = title.replace('[', '').replace(']', '').replace('#', '')
            lines.append(f"{i}. [{title}](#{i}-{self._slugify(title)})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 论文详情
        for i, paper in enumerate(papers, 1):
            paper_md = self._generate_single_paper(
                paper, i, include_ai_summary, include_translation, include_insights
            )
            lines.append(paper_md)
            lines.append("")
            lines.append("---")
            lines.append("")

        # 页脚
        lines.append("## 关于")
        lines.append("")
        lines.append("本文档由 **ArXiv 论文自动抓取工具** 自动生成。")
        lines.append("")
        lines.append("- 数据来源: [arXiv.org](https://arxiv.org/)")
        if include_ai_summary:
            lines.append("- AI 总结: 由 AI 模型自动生成，仅供参考")
        lines.append("")

        return '\n'.join(lines)

    def _generate_single_paper(
        self,
        paper: Dict[str, Any],
        index: int,
        include_ai_summary: bool,
        include_translation: bool,
        include_insights: bool = True
    ) -> str:
        """
        生成单篇论文的 Markdown

        Args:
            paper: 论文数据
            index: 论文序号
            include_ai_summary: 是否包含 AI 总结
            include_translation: 是否包含翻译
            include_insights: 是否包含关键洞察

        Returns:
            单篇论文的 Markdown 内容
        """
        lines = []

        # 标题
        title = paper.get('title', 'N/A')
        lines.append(f"## {index}. {title}")
        lines.append("")

        # 基本信息
        lines.append("### 📋 基本信息")
        lines.append("")

        # ArXiv ID 和链接
        arxiv_id = paper.get('arxiv_id', 'N/A')
        if arxiv_id != 'N/A':
            lines.append(f"- **ArXiv ID**: [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})")
            pdf_url = paper.get('pdf_url', f"https://arxiv.org/pdf/{arxiv_id}")
            lines.append(f"- **PDF 链接**: [下载]({pdf_url})")
        else:
            lines.append(f"- **ArXiv ID**: {arxiv_id}")

        # 作者
        authors = paper.get('authors', [])
        if authors:
            author_str = ', '.join(authors[:5])
            if len(authors) > 5:
                author_str += f' 等 {len(authors)} 位作者'
            lines.append(f"- **作者**: {author_str}")

        # 发布时间
        published = paper.get('published', 'N/A')
        if published != 'N/A':
            # 格式化时间
            try:
                from dateutil import parser
                pub_date = parser.parse(published)
                lines.append(f"- **发布时间**: {pub_date.strftime('%Y-%m-%d')}")
            except:
                lines.append(f"- **发布时间**: {published}")

        # 分类
        categories = paper.get('categories', [])
        if categories:
            cat_badges = ' '.join([f"`{cat}`" for cat in categories[:5]])
            lines.append(f"- **分类**: {cat_badges}")

        lines.append("")

        # 关键洞察（放在最前面，方便快速浏览）
        if include_insights and 'insights' in paper:
            lines.append("### 💡 关键洞察")
            lines.append("")
            insights_data = paper.get('insights', {})
            insights_list = insights_data.get('insights', [])
            status = insights_data.get('status', 'unknown')

            if status == 'success' and insights_list:
                for insight in insights_list:
                    lines.append(f"- {insight}")
            else:
                lines.append("> 洞察提取失败或未启用")
            lines.append("")

        # 原文摘要
        lines.append("### 📝 原文摘要")
        lines.append("")
        summary = paper.get('summary', 'N/A')
        if summary != 'N/A':
            # 清理摘要文本
            summary = summary.strip().replace('\n', ' ')
            lines.append(f"> {summary}")
        else:
            lines.append("> 暂无摘要")
        lines.append("")

        # 翻译
        if include_translation and 'translation' in paper:
            lines.append("### 🌐 中文翻译")
            lines.append("")
            translation = paper.get('translation', '')
            if translation:
                lines.append(f"> {translation}")
            else:
                lines.append("> 翻译失败或未启用")
            lines.append("")

        # AI 总结
        if include_ai_summary and 'ai_summary' in paper:
            lines.append("### 🤖 AI 智能总结")
            lines.append("")
            ai_summary = paper.get('ai_summary', {})
            summary_text = ai_summary.get('summary', '')
            status = ai_summary.get('status', 'unknown')

            if status == 'success' and summary_text:
                lines.append(summary_text)
            else:
                lines.append("> AI 总结生成失败或未启用")
            lines.append("")

        # 额外信息（如果有）
        comment = paper.get('comment')
        journal_ref = paper.get('journal_ref')
        doi = paper.get('doi')

        if any([comment, journal_ref, doi]):
            lines.append("### ℹ️ 其他信息")
            lines.append("")
            if comment:
                lines.append(f"- **备注**: {comment}")
            if journal_ref:
                lines.append(f"- **期刊引用**: {journal_ref}")
            if doi:
                lines.append(f"- **DOI**: [{doi}](https://doi.org/{doi})")
            lines.append("")

        return '\n'.join(lines)

    def _slugify(self, text: str) -> str:
        """
        将文本转换为 URL slug 格式

        Args:
            text: 原始文本

        Returns:
            slug 格式的文本
        """
        # 简单实现：移除特殊字符，替换空格为连字符
        text = text.lower()
        text = ''.join(c if c.isalnum() or c.isspace() else '' for c in text)
        text = '-'.join(text.split())
        return text[:50]  # 限制长度

    def save_to_file(self, content: str, file_path: str) -> bool:
        """
        保存 Markdown 内容到文件

        Args:
            content: Markdown 内容
            file_path: 文件路径

        Returns:
            是否保存成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Markdown 文档已保存到: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存 Markdown 文档失败: {str(e)}")
            return False

    def generate_html(self, markdown_content: str) -> str:
        """
        将 Markdown 转换为 HTML（可选功能）

        Args:
            markdown_content: Markdown 内容

        Returns:
            HTML 内容
        """
        try:
            import markdown
            html = markdown.markdown(
                markdown_content,
                extensions=['extra', 'codehilite', 'toc']
            )
            return self._wrap_html(html)
        except ImportError:
            self.logger.warning("markdown 库未安装，无法转换为 HTML")
            return ""
        except Exception as e:
            self.logger.error(f"Markdown 转 HTML 失败: {str(e)}")
            return ""

    def _wrap_html(self, body: str) -> str:
        """
        为 HTML 内容添加完整的 HTML 结构

        Args:
            body: HTML 正文

        Returns:
            完整的 HTML 文档
        """
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv 论文日报</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h1 {{ font-size: 2.5em; }}
        h2 {{ font-size: 2em; margin-top: 40px; }}
        h3 {{ font-size: 1.5em; margin-top: 30px; }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #555;
            background-color: #f9f9f9;
            padding: 15px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 2px solid #eee;
            margin: 40px 0;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
{body}
</body>
</html>"""