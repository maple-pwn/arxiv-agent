"""
AI 服务模块
提供论文总结和翻译功能
支持多种 AI API：OpenAI、Anthropic、Ollama 等
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from .prompt_loader import get_prompt_loader


class AIServiceError(Exception):
    """AI 服务异常"""
    pass


class BaseAIService(ABC):
    """AI 服务基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 AI 服务

        Args:
            config: AI 服务配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """
        总结论文

        Args:
            paper: 论文数据

        Returns:
            包含总结内容的字典
        """
        pass

    @abstractmethod
    def translate_text(self, text: str, target_lang: str = "zh") -> str:
        """
        翻译文本

        Args:
            text: 原文
            target_lang: 目标语言

        Returns:
            翻译后的文本
        """
        pass

    @abstractmethod
    def extract_insights(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取论文的关键洞察

        Args:
            paper: 论文数据

        Returns:
            包含洞察内容的字典
        """
        pass


class OpenAIService(BaseAIService):
    """OpenAI API 服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.7)
        self.prompt_loader = get_prompt_loader()

        if not self.api_key:
            raise AIServiceError("OpenAI API key 未配置")

    def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """
        调用 OpenAI API

        Args:
            messages: 消息列表

        Returns:
            API 响应文本
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': self.model,
                'messages': messages,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }

            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            return result['choices'][0]['message']['content'].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenAI API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get('title', 'N/A')
        authors = ', '.join(paper.get('authors', [])[:3])
        summary = paper.get('summary', '')

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            'summarize',
            title=title,
            authors=authors,
            summary=summary
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            summary_text = self._call_api(messages)
            return {
                'summary': summary_text,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {
                'summary': f"总结生成失败: {str(e)}",
                'status': 'error'
            }

    def translate_text(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        if target_lang == "zh":
            lang_name = "中文"
        else:
            lang_name = target_lang

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            'translate',
            lang_name=lang_name,
            text=text
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            return self._call_api(messages)
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return f"翻译失败: {str(e)}"

    def extract_insights(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键洞察（增强版）"""
        title = paper.get('title', 'N/A')
        summary = paper.get('summary', '')

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            'insights',
            title=title,
            summary=summary
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            import json as json_lib
            response_text = self._call_api(messages)

            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（处理可能的 markdown 代码块）
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()

                insights_data = json_lib.loads(response_text)
                return {
                    'insights': insights_data.get('insights', []),
                    'status': 'success'
                }
            except:
                # 如果 JSON 解析失败，尝试从文本中提取
                insights = []
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('洞察')):
                        cleaned = line.lstrip('-•').strip()
                        if cleaned:
                            insights.append(cleaned)

                return {
                    'insights': insights[:5],  # 最多5个
                    'status': 'success'
                }

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {
                'insights': [],
                'status': 'error',
                'error': str(e)
            }


class AnthropicService(BaseAIService):
    """Anthropic Claude API 服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'claude-3-5-sonnet-20241022')
        self.base_url = config.get('base_url', 'https://api.anthropic.com/v1')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.7)
        self.prompt_loader = get_prompt_loader()

        if not self.api_key:
            raise AIServiceError("Anthropic API key 未配置")

    def _call_api(self, prompt: str, system: str = None) -> str:
        """
        调用 Anthropic API

        Args:
            prompt: 用户提示词
            system: 系统提示词

        Returns:
            API 响应文本
        """
        try:
            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }

            data = {
                'model': self.model,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            }

            if system:
                data['system'] = system

            response = requests.post(
                f'{self.base_url}/messages',
                headers=headers,
                json=data,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            return result['content'][0]['text'].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Anthropic API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get('title', 'N/A')
        authors = ', '.join(paper.get('authors', [])[:3])
        summary = paper.get('summary', '')

        prompt = f"""请对以下学术论文进行总结分析，要求：

1. **核心观点**：用 2-3 句话概括论文的主要贡献和创新点
2. **研究方法**：简要说明使用的技术方法或理论框架
3. **关键结果**：总结主要实验结果或理论发现
4. **应用价值**：说明研究的实际应用场景或学术意义

论文信息：
标题：{title}
作者：{authors}
摘要：{summary}

请用中文输出，使用清晰的结构化格式。"""

        system = "你是一位专业的学术论文分析专家，擅长提炼论文核心要点。"

        try:
            summary_text = self._call_api(prompt, system)
            return {
                'summary': summary_text,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {
                'summary': f"总结生成失败: {str(e)}",
                'status': 'error'
            }

    def translate_text(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        if target_lang == "zh":
            lang_name = "中文"
        else:
            lang_name = target_lang

        prompt = f"请将以下英文学术摘要翻译成{lang_name}，要求翻译准确、专业、流畅：\n\n{text}"
        system = "你是一位专业的学术翻译专家。"

        try:
            return self._call_api(prompt, system)
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return f"翻译失败: {str(e)}"

    def extract_insights(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键洞察"""
        title = paper.get('title', 'N/A')
        summary = paper.get('summary', '')

        prompt = f"""请从以下学术论文中提取 3-5 个关键洞察（Key Insights），每个洞察应该是一句话概括（不超过30个字）。

论文信息：
标题：{title}
摘要：{summary}

请列出关键洞察（每行一个，以 - 开头）："""

        system = "你是一位专业的学术研究洞察专家。"

        try:
            response_text = self._call_api(prompt, system)
            insights = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('洞察')):
                    cleaned = line.lstrip('-•').strip()
                    if cleaned:
                        insights.append(cleaned)

            return {
                'insights': insights[:5],
                'status': 'success'
            }

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {
                'insights': [],
                'status': 'error',
                'error': str(e)
            }


class OllamaService(BaseAIService):
    """Ollama 本地模型服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get('model', 'llama2')
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.prompt_loader = get_prompt_loader()

    def _call_api(self, prompt: str, system: str = None) -> str:
        """
        调用 Ollama API

        Args:
            prompt: 用户提示词
            system: 系统提示词

        Returns:
            API 响应文本
        """
        try:
            data = {
                'model': self.model,
                'prompt': prompt,
                'stream': False
            }

            if system:
                data['system'] = system

            response = requests.post(
                f'{self.base_url}/api/generate',
                json=data,
                timeout=120
            )

            response.raise_for_status()
            result = response.json()

            return result['response'].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get('title', 'N/A')
        authors = ', '.join(paper.get('authors', [])[:3])
        summary = paper.get('summary', '')

        prompt = f"""请对以下学术论文进行总结分析，要求：

1. **核心观点**：用 2-3 句话概括论文的主要贡献和创新点
2. **研究方法**：简要说明使用的技术方法或理论框架
3. **关键结果**：总结主要实验结果或理论发现
4. **应用价值**：说明研究的实际应用场景或学术意义

论文信息：
标题：{title}
作者：{authors}
摘要：{summary}

请用中文输出，使用清晰的结构化格式。"""

        system = "你是一位专业的学术论文分析专家，擅长提炼论文核心要点。"

        try:
            summary_text = self._call_api(prompt, system)
            return {
                'summary': summary_text,
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {
                'summary': f"总结生成失败: {str(e)}",
                'status': 'error'
            }

    def translate_text(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        if target_lang == "zh":
            lang_name = "中文"
        else:
            lang_name = target_lang

        prompt = f"请将以下英文学术摘要翻译成{lang_name}，要求翻译准确、专业、流畅：\n\n{text}"
        system = "你是一位专业的学术翻译专家。"

        try:
            return self._call_api(prompt, system)
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return f"翻译失败: {str(e)}"

    def extract_insights(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键洞察"""
        title = paper.get('title', 'N/A')
        summary = paper.get('summary', '')

        prompt = f"""请从以下学术论文中提取 3-5 个关键洞察（Key Insights），每个洞察应该是一句话概括（不超过30个字）。

论文信息：
标题：{title}
摘要：{summary}

请列出关键洞察（每行一个，以 - 开头）："""

        system = "你是一位专业的学术研究洞察专家。"

        try:
            response_text = self._call_api(prompt, system)
            insights = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('洞察')):
                    cleaned = line.lstrip('-•').strip()
                    if cleaned:
                        insights.append(cleaned)

            return {
                'insights': insights[:5],
                'status': 'success'
            }

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {
                'insights': [],
                'status': 'error',
                'error': str(e)
            }


def create_ai_service(config: Dict[str, Any]) -> Optional[BaseAIService]:
    """
    创建 AI 服务实例

    Args:
        config: AI 配置字典

    Returns:
        AI 服务实例
    """
    if not config.get('enabled', False):
        return None

    provider = config.get('provider', 'openai').lower()

    try:
        if provider == 'openai':
            return OpenAIService(config.get('openai', {}))
        elif provider == 'anthropic' or provider == 'claude':
            return AnthropicService(config.get('anthropic', {}))
        elif provider == 'ollama':
            return OllamaService(config.get('ollama', {}))
        else:
            logging.warning(f"不支持的 AI 服务提供商: {provider}")
            return None

    except AIServiceError as e:
        logging.error(f"创建 AI 服务失败: {str(e)}")
        return None