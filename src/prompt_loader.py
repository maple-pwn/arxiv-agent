"""
Prompt加载模块
从YAML文件加载和管理AI提示词
"""

import os
import yaml
import logging
from typing import Dict, Any


class PromptLoader:
    """Prompt加载器"""

    def __init__(self, prompts_file: str = "./prompts/prompts.yaml"):
        """
        初始化Prompt加载器

        Args:
            prompts_file: prompts配置文件路径
        """
        self.prompts_file = prompts_file
        self.logger = logging.getLogger(__name__)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """加载prompts配置"""
        if not os.path.exists(self.prompts_file):
            self.logger.warning(
                f"Prompts文件不存在: {self.prompts_file}，使用默认prompts"
            )
            return self._get_default_prompts()

        try:
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                prompts = yaml.safe_load(f)
                self.logger.info(f"已从 {self.prompts_file} 加载prompts")
                return prompts or {}
        except Exception as e:
            self.logger.error(f"加载prompts文件失败: {str(e)}")
            return self._get_default_prompts()

    def get_prompt(self, prompt_type: str, **kwargs) -> tuple[str, str]:
        """
        获取指定类型的prompt

        Args:
            prompt_type: prompt类型（summarize, translate, insights等）
            **kwargs: 模板变量

        Returns:
            (system_prompt, user_prompt)
        """
        if prompt_type not in self.prompts:
            self.logger.warning(f"未找到prompt类型: {prompt_type}，使用默认prompt")
            return "", ""

        prompt_config = self.prompts[prompt_type]
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        try:
            # 使用format格式化模板
            user_prompt = user_template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"模板变量缺失: {str(e)}")
            user_prompt = user_template

        return system_prompt, user_prompt

    def get_custom_prompt(self, custom_name: str, **kwargs) -> tuple[str, str]:
        """
        获取自定义prompt

        Args:
            custom_name: 自定义prompt名称
            **kwargs: 模板变量

        Returns:
            (system_prompt, user_prompt)
        """
        if "custom" not in self.prompts or custom_name not in self.prompts["custom"]:
            self.logger.warning(f"未找到自定义prompt: {custom_name}")
            return "", ""

        prompt_config = self.prompts["custom"][custom_name]
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        try:
            user_prompt = user_template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"模板变量缺失: {str(e)}")
            user_prompt = user_template

        return system_prompt, user_prompt

    def _get_default_prompts(self) -> Dict[str, Any]:
        """获取默认prompts"""
        return {
            "summarize": {
                "system": "你是一位专业的学术论文分析专家，擅长提炼论文核心要点。",
                "user_template": """请对以下学术论文进行总结分析，要求：

1. **核心观点**：用 2-3 句话概括论文的主要贡献和创新点
2. **研究方法**：简要说明使用的技术方法或理论框架
3. **关键结果**：总结主要实验结果或理论发现
4. **应用价值**：说明研究的实际应用场景或学术意义

论文信息：
标题：{title}
作者：{authors}
摘要：{summary}

请用中文输出，使用清晰的结构化格式。""",
            },
            "translate": {
                "system": "你是一位专业的学术翻译专家。",
                "user_template": "请将以下英文学术摘要翻译成{lang_name}，要求翻译准确、专业、流畅：\n\n{text}",
            },
            "insights": {
                "system": "你是一位专业的学术研究洞察专家，擅长从论文中提炼关键见解。",
                "user_template": """请从以下学术论文中提取关键洞察，每个洞察应简洁明了、富有启发性。

论文信息：
标题：{title}
摘要：{summary}

请以 JSON 格式输出，格式如下：
{{
  "insights": [
    "洞察1：简短描述（不超过30字）",
    "洞察2：简短描述（不超过30字）",
    "洞察3：简短描述（不超过30字）"
  ]
}}""",
            },
        }


# 全局prompt加载器实例
_prompt_loader = None


def get_prompt_loader(prompts_file: str = "./prompts/prompts.yaml") -> PromptLoader:
    """
    获取全局prompt加载器实例

    Args:
        prompts_file: prompts配置文件路径

    Returns:
        PromptLoader实例
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader(prompts_file)
    return _prompt_loader
