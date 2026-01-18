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
from .utils import create_retry_session


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

    @abstractmethod
    def filter_paper(
        self, paper: Dict[str, Any], filter_keywords: str
    ) -> Dict[str, Any]:
        """
        判断论文是否与筛选关键词相关

        Args:
            paper: 论文数据
            filter_keywords: 筛选关键词

        Returns:
            包含筛选结果的字典：
            {
                'relevant': bool,  # 是否相关
                'confidence': float,  # 置信度 (0.0-1.0)
                'reason': str,  # 判断理由
                'status': str  # 'success' or 'error'
            }
        """
        pass


class OpenAIService(BaseAIService):
    """OpenAI API 服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
        self.request_timeout = config.get("request_timeout", 60)
        self.session = create_retry_session(
            total_retries=int(config.get("max_retries", 3)),
            backoff_factor=float(config.get("backoff_factor", 0.5)),
        )
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
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.request_timeout,
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenAI API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get("title", "N/A")
        authors = ", ".join(paper.get("authors", [])[:3])
        summary = paper.get("summary", "")

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "summarize", title=title, authors=authors, summary=summary
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            summary_text = self._call_api(messages)
            return {"summary": summary_text, "status": "success"}
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {"summary": f"总结生成失败: {str(e)}", "status": "error"}

    def translate_text(self, text: str, target_lang: str = "zh") -> str:
        """翻译文本"""
        if target_lang == "zh":
            lang_name = "中文"
        else:
            lang_name = target_lang

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "translate", lang_name=lang_name, text=text
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            return self._call_api(messages)
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return f"翻译失败: {str(e)}"

    def extract_insights(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """提取论文关键洞察（增强版）"""
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "insights", title=title, summary=summary
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            import json as json_lib

            response_text = self._call_api(messages)

            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（处理可能的 markdown 代码块）
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                insights_data = json_lib.loads(response_text)
                return {
                    "insights": insights_data.get("insights", []),
                    "status": "success",
                }
            except (json_lib.JSONDecodeError, ValueError, KeyError):
                insights = []
                for line in response_text.split("\n"):
                    line = line.strip()
                    if line and (
                        line.startswith("-")
                        or line.startswith("•")
                        or line.startswith("洞察")
                    ):
                        cleaned = line.lstrip("-•").strip()
                        if cleaned:
                            insights.append(cleaned)

                return {
                    "insights": insights[:5],  # 最多5个
                    "status": "success",
                }

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {"insights": [], "status": "error", "error": str(e)}

    def filter_paper(
        self, paper: Dict[str, Any], filter_keywords: str
    ) -> Dict[str, Any]:
        """判断论文相关性"""
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "filter", filter_keywords=filter_keywords, title=title, summary=summary
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            import json as json_lib

            response_text = self._call_api(messages)

            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（处理可能的 markdown 代码块）
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                filter_result = json_lib.loads(response_text)
                return {
                    "relevant": filter_result.get("relevant", False),
                    "confidence": float(filter_result.get("confidence", 0.0)),
                    "reason": filter_result.get("reason", ""),
                    "status": "success",
                }
            except (json_lib.JSONDecodeError, ValueError, KeyError):
                self.logger.warning(f"筛选结果JSON解析失败，保留论文: {title[:50]}")
                return {
                    "relevant": True,
                    "confidence": 0.5,
                    "reason": "JSON解析失败，默认保留",
                    "status": "success",
                }

        except Exception as e:
            self.logger.error(f"论文筛选失败: {str(e)}")
            return {
                "relevant": True,
                "confidence": 0.5,
                "reason": f"筛选失败: {str(e)}",
                "status": "error",
            }


class AnthropicService(BaseAIService):
    """Anthropic Claude API 服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
        self.request_timeout = config.get("request_timeout", 60)
        self.session = create_retry_session(
            total_retries=int(config.get("max_retries", 3)),
            backoff_factor=float(config.get("backoff_factor", 0.5)),
        )
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
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system:
                data["system"] = system

            response = self.session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=self.request_timeout,
            )

            response.raise_for_status()
            result = response.json()

            return result["content"][0]["text"].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Anthropic API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get("title", "N/A")
        authors = ", ".join(paper.get("authors", [])[:3])
        summary = paper.get("summary", "")

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
            return {"summary": summary_text, "status": "success"}
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {"summary": f"总结生成失败: {str(e)}", "status": "error"}

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
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        prompt = f"""请从以下学术论文中提取 3-5 个关键洞察（Key Insights），每个洞察应该是一句话概括（不超过30个字）。

论文信息：
标题：{title}
摘要：{summary}

请列出关键洞察（每行一个，以 - 开头）："""

        system = "你是一位专业的学术研究洞察专家。"

        try:
            response_text = self._call_api(prompt, system)
            insights = []
            for line in response_text.split("\n"):
                line = line.strip()
                if line and (
                    line.startswith("-")
                    or line.startswith("•")
                    or line.startswith("洞察")
                ):
                    cleaned = line.lstrip("-•").strip()
                    if cleaned:
                        insights.append(cleaned)

            return {"insights": insights[:5], "status": "success"}

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {"insights": [], "status": "error", "error": str(e)}

    def filter_paper(
        self, paper: Dict[str, Any], filter_keywords: str
    ) -> Dict[str, Any]:
        """判断论文相关性"""
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "filter", filter_keywords=filter_keywords, title=title, summary=summary
        )

        try:
            import json as json_lib

            response_text = self._call_api(user_prompt, system_prompt)

            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（处理可能的 markdown 代码块）
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                filter_result = json_lib.loads(response_text)
                return {
                    "relevant": filter_result.get("relevant", False),
                    "confidence": float(filter_result.get("confidence", 0.0)),
                    "reason": filter_result.get("reason", ""),
                    "status": "success",
                }
            except (json_lib.JSONDecodeError, ValueError, KeyError):
                self.logger.warning(f"筛选结果JSON解析失败，保留论文: {title[:50]}")
                return {
                    "relevant": True,
                    "confidence": 0.5,
                    "reason": "JSON解析失败，默认保留",
                    "status": "success",
                }

        except Exception as e:
            self.logger.error(f"论文筛选失败: {str(e)}")
            return {
                "relevant": True,
                "confidence": 0.5,
                "reason": f"筛选失败: {str(e)}",
                "status": "error",
            }


class OllamaService(BaseAIService):
    """Ollama 本地模型服务"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model", "llama2")
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.request_timeout = config.get("request_timeout", 120)
        self.session = create_retry_session(
            total_retries=int(config.get("max_retries", 3)),
            backoff_factor=float(config.get("backoff_factor", 0.5)),
        )
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
            data = {"model": self.model, "prompt": prompt, "stream": False}

            if system:
                data["system"] = system

            response = self.session.post(
                f"{self.base_url}/api/generate", json=data, timeout=self.request_timeout
            )

            response.raise_for_status()
            result = response.json()

            return result["response"].strip()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama API 调用失败: {str(e)}")
            raise AIServiceError(f"API 调用失败: {str(e)}")

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """总结论文"""
        title = paper.get("title", "N/A")
        authors = ", ".join(paper.get("authors", [])[:3])
        summary = paper.get("summary", "")

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
            return {"summary": summary_text, "status": "success"}
        except Exception as e:
            self.logger.error(f"论文总结失败: {str(e)}")
            return {"summary": f"总结生成失败: {str(e)}", "status": "error"}

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
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        prompt = f"""请从以下学术论文中提取 3-5 个关键洞察（Key Insights），每个洞察应该是一句话概括（不超过30个字）。

论文信息：
标题：{title}
摘要：{summary}

请列出关键洞察（每行一个，以 - 开头）："""

        system = "你是一位专业的学术研究洞察专家。"

        try:
            response_text = self._call_api(prompt, system)
            insights = []
            for line in response_text.split("\n"):
                line = line.strip()
                if line and (
                    line.startswith("-")
                    or line.startswith("•")
                    or line.startswith("洞察")
                ):
                    cleaned = line.lstrip("-•").strip()
                    if cleaned:
                        insights.append(cleaned)

            return {"insights": insights[:5], "status": "success"}

        except Exception as e:
            self.logger.error(f"提取洞察失败: {str(e)}")
            return {"insights": [], "status": "error", "error": str(e)}

    def filter_paper(
        self, paper: Dict[str, Any], filter_keywords: str
    ) -> Dict[str, Any]:
        """判断论文相关性"""
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "")

        # 从prompt_loader获取prompt
        system_prompt, user_prompt = self.prompt_loader.get_prompt(
            "filter", filter_keywords=filter_keywords, title=title, summary=summary
        )

        try:
            import json as json_lib

            response_text = self._call_api(user_prompt, system_prompt)

            # 尝试解析 JSON
            try:
                # 提取 JSON 部分（处理可能的 markdown 代码块）
                if "```json" in response_text:
                    response_text = (
                        response_text.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in response_text:
                    response_text = (
                        response_text.split("```")[1].split("```")[0].strip()
                    )

                filter_result = json_lib.loads(response_text)
                return {
                    "relevant": filter_result.get("relevant", False),
                    "confidence": float(filter_result.get("confidence", 0.0)),
                    "reason": filter_result.get("reason", ""),
                    "status": "success",
                }
            except (json_lib.JSONDecodeError, ValueError, KeyError):
                self.logger.warning(f"筛选结果JSON解析失败，保留论文: {title[:50]}")
                return {
                    "relevant": True,
                    "confidence": 0.5,
                    "reason": "JSON解析失败，默认保留",
                    "status": "success",
                }

        except Exception as e:
            self.logger.error(f"论文筛选失败: {str(e)}")
            return {
                "relevant": True,
                "confidence": 0.5,
                "reason": f"筛选失败: {str(e)}",
                "status": "error",
            }


def _merge_provider_config(
    ai_config: Dict[str, Any], provider_key: str
) -> Dict[str, Any]:
    """
    合并全局 AI 配置与提供商配置

    Args:
        ai_config: 全局 AI 配置
        provider_key: 提供商键（openai/anthropic/ollama）

    Returns:
        合并后的配置字典
    """
    provider_config = dict(ai_config.get(provider_key, {}))
    for key in ["max_retries", "backoff_factor", "request_timeout"]:
        if key in ai_config and key not in provider_config:
            provider_config[key] = ai_config[key]
    return provider_config


def create_ai_service(config: Dict[str, Any]) -> Optional[BaseAIService]:
    """
    创建 AI 服务实例

    Args:
        config: AI 配置字典

    Returns:
        AI 服务实例
    """
    if not config.get("enabled", False):
        return None

    provider = config.get("provider", "openai").lower()
    provider_key = "anthropic" if provider in ["anthropic", "claude"] else provider

    try:
        if provider_key == "openai":
            return OpenAIService(_merge_provider_config(config, "openai"))
        elif provider_key == "anthropic":
            return AnthropicService(_merge_provider_config(config, "anthropic"))
        elif provider_key == "ollama":
            return OllamaService(_merge_provider_config(config, "ollama"))
        else:
            logging.warning(f"不支持的 AI 服务提供商: {provider_key}")
            return None

    except AIServiceError as e:
        logging.error(f"创建 AI 服务失败: {str(e)}")
        return None
