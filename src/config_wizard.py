"""
交互式配置向导模块
提供中文界面的配置文件生成向导
"""

import os
from typing import Dict, Any, List, Optional, Tuple
import yaml


class ConfigWizard:
    """交互式配置向导"""

    # ArXiv 常用分类
    ARXIV_CATEGORIES = {
        "1": ("cs.AI", "人工智能"),
        "2": ("cs.LG", "机器学习"),
        "3": ("cs.CV", "计算机视觉"),
        "4": ("cs.CL", "自然语言处理"),
        "5": ("cs.CR", "密码学与安全"),
        "6": ("cs.SE", "软件工程"),
        "7": ("cs.NI", "网络与互联网"),
        "8": ("cs.DC", "分布式计算"),
        "9": ("stat.ML", "统计机器学习"),
        "10": ("math.OC", "优化与控制"),
    }

    # AI 提供商
    AI_PROVIDERS = {
        "1": ("openai", "OpenAI (GPT系列)"),
        "2": ("anthropic", "Anthropic (Claude系列)"),
        "3": ("ollama", "Ollama (本地模型)"),
    }

    # 通知方式
    NOTIFICATION_METHODS = {
        "1": ("email", "邮件通知"),
        "2": ("webhook", "Webhook推送"),
        "3": ("none", "不启用通知"),
    }

    def __init__(self):
        """初始化配置向导"""
        self.config: Dict[str, Any] = {}

    def run(self) -> Optional[Dict[str, Any]]:
        """
        运行交互式配置向导

        Returns:
            生成的配置字典，如果取消则返回 None
        """
        self._print_header()

        try:
            # 步骤1: ArXiv 搜索配置
            if not self._step_arxiv():
                return None

            # 步骤2: AI 配置
            if not self._step_ai():
                return None

            # 步骤3: 通知配置
            if not self._step_notification():
                return None

            # 步骤4: 存储配置
            if not self._step_storage():
                return None

            # 步骤5: 定时任务配置
            if not self._step_schedule():
                return None

            # 确认并保存
            return self._confirm_and_save()

        except KeyboardInterrupt:
            print("\n\n⚠️  配置向导已取消")
            return None

    def _print_header(self) -> None:
        """打印欢迎信息"""
        print("\n" + "=" * 60)
        print("🚀 ArXiv 论文抓取工具 - 交互式配置向导")
        print("=" * 60)
        print("\n欢迎使用配置向导！我们将引导您完成配置文件的创建。")
        print("按 Ctrl+C 可随时取消。\n")

    def _input(self, prompt: str, default: str = "") -> str:
        """带默认值的输入"""
        if default:
            result = input(f"{prompt} [{default}]: ").strip()
            return result if result else default
        return input(f"{prompt}: ").strip()

    def _input_yes_no(self, prompt: str, default: bool = True) -> bool:
        """是/否输入"""
        default_str = "Y/n" if default else "y/N"
        result = input(f"{prompt} ({default_str}): ").strip().lower()
        if not result:
            return default
        return result in ("y", "yes", "是", "对", "true", "1")

    def _input_choice(
        self,
        prompt: str,
        choices: Dict[str, Tuple[str, str]],
        allow_multiple: bool = False,
    ) -> List[str]:
        """选择输入"""
        print(f"\n{prompt}")
        for key, (value, desc) in choices.items():
            print(f"  {key}. {desc} ({value})")

        if allow_multiple:
            print("\n提示: 可输入多个选项，用逗号分隔，如: 1,2,3")
            result = input("\n请选择: ").strip()
            selected = []
            for choice in result.replace("，", ",").split(","):
                choice = choice.strip()
                if choice in choices:
                    selected.append(choices[choice][0])
            return selected if selected else [choices["1"][0]]
        else:
            result = input("\n请选择: ").strip()
            if result in choices:
                return [choices[result][0]]
            return [choices["1"][0]]

    def _step_arxiv(self) -> bool:
        """步骤1: ArXiv 搜索配置"""
        print("\n" + "-" * 50)
        print("📚 步骤 1/5: ArXiv 搜索配置")
        print("-" * 50)

        # 关键词
        print("\n请输入搜索关键词（用于在 ArXiv 上搜索论文）")
        print("提示: 多个关键词用逗号分隔，关键词之间是 OR 关系")
        keywords_str = self._input("搜索关键词", "machine learning, deep learning")
        keywords = [
            kw.strip()
            for kw in keywords_str.replace("，", ",").split(",")
            if kw.strip()
        ]

        # 分类
        categories = self._input_choice(
            "请选择 ArXiv 分类（可多选）:", self.ARXIV_CATEGORIES, allow_multiple=True
        )

        # 最大结果数
        max_results_str = self._input("每次抓取的最大论文数量", "50")
        try:
            max_results = int(max_results_str)
            if max_results <= 0:
                max_results = 50
        except ValueError:
            max_results = 50

        # 相关度评分
        enable_relevance = self._input_yes_no("是否启用相关度评分（推荐）", True)

        self.config["arxiv"] = {
            "keywords": keywords,
            "categories": categories,
            "max_results": max_results,
            "sort_by": "submittedDate",
            "sort_order": "descending",
            "enable_relevance_score": enable_relevance,
        }

        # 多级排序
        if enable_relevance:
            self.config["arxiv"]["multi_level_sort"] = [
                {"field": "relevance_score", "order": "descending"},
                {"field": "submittedDate", "order": "descending"},
            ]

        print("\n✅ ArXiv 搜索配置完成")
        return True

    def _step_ai(self) -> bool:
        """步骤2: AI 配置"""
        print("\n" + "-" * 50)
        print("🤖 步骤 2/5: AI 智能分析配置")
        print("-" * 50)

        enable_ai = self._input_yes_no("\n是否启用 AI 智能分析功能", True)

        if not enable_ai:
            self.config["ai"] = {"enabled": False}
            print("\n✅ AI 功能已禁用")
            return True

        # 选择提供商
        providers = self._input_choice(
            "请选择 AI 服务提供商:", self.AI_PROVIDERS, allow_multiple=False
        )
        provider = providers[0]

        ai_config: Dict[str, Any] = {
            "enabled": True,
            "provider": provider,
            "enable_summary": True,
            "enable_translation": True,
            "enable_insights": True,
            "max_workers": 4,
            "max_retries": 3,
            "request_timeout": 120,
        }

        # 根据提供商配置
        if provider == "openai":
            ai_config.update(self._config_openai())
        elif provider == "anthropic":
            ai_config.update(self._config_anthropic())
        elif provider == "ollama":
            ai_config.update(self._config_ollama())

        # AI 筛选
        print("\n" + "-" * 30)
        print("🎯 AI 智能筛选（可选）")
        print("-" * 30)
        print("\nAI 筛选可以在处理前过滤不相关的论文，节省 API 成本。")
        enable_filter = self._input_yes_no("是否启用 AI 智能筛选", False)

        if enable_filter:
            print("\n请输入筛选关键词（用于判断论文相关性）")
            print("提示: 与搜索关键词不同，筛选关键词应该更具体")
            filter_keywords = self._input("筛选关键词", "")
            if filter_keywords:
                ai_config["enable_filter"] = True
                ai_config["filter_keywords"] = filter_keywords
                ai_config["filter_threshold"] = 0.7

        # Markdown 报告
        ai_config["send_markdown_report"] = self._input_yes_no(
            "\n是否生成 Markdown 报告", True
        )
        if ai_config["send_markdown_report"]:
            ai_config["markdown_dir"] = "./data/reports"

        self.config["ai"] = ai_config
        print("\n✅ AI 配置完成")
        return True

    def _config_openai(self) -> Dict[str, Any]:
        """配置 OpenAI"""
        print("\n" + "-" * 30)
        print("🔧 OpenAI 配置")
        print("-" * 30)

        api_key = self._input("\nAPI Key（必填）", "")
        if not api_key:
            print("⚠️  未提供 API Key，请稍后在配置文件中填写")
            api_key = "your-api-key-here"

        print("\n常用 API 端点:")
        print("  1. OpenAI 官方: https://api.openai.com/v1")
        print("  2. 硅基流动: https://api.siliconflow.cn/v1")
        print("  3. 其他兼容端点")
        base_url = self._input("API 端点", "https://api.openai.com/v1")

        print("\n常用模型:")
        print("  - gpt-3.5-turbo (便宜快速)")
        print("  - gpt-4o-mini (性价比高)")
        print("  - gpt-4o (质量最高)")
        print("  - deepseek-ai/DeepSeek-V3 (硅基流动)")
        model = self._input("模型名称", "gpt-3.5-turbo")

        return {
            "openai": {
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "max_tokens": 1000,
                "temperature": 0.7,
            }
        }

    def _config_anthropic(self) -> Dict[str, Any]:
        """配置 Anthropic"""
        print("\n" + "-" * 30)
        print("🔧 Anthropic (Claude) 配置")
        print("-" * 30)

        api_key = self._input("\nAPI Key（必填）", "")
        if not api_key:
            print("⚠️  未提供 API Key，请稍后在配置文件中填写")
            api_key = "your-api-key-here"

        print("\n常用模型:")
        print("  - claude-3-5-sonnet-20241022 (推荐)")
        print("  - claude-3-opus-20240229 (最强)")
        print("  - claude-3-haiku-20240307 (最快)")
        model = self._input("模型名称", "claude-3-5-sonnet-20241022")

        return {
            "anthropic": {
                "api_key": api_key,
                "base_url": "https://api.anthropic.com/v1",
                "model": model,
                "max_tokens": 1000,
                "temperature": 0.7,
            }
        }

    def _config_ollama(self) -> Dict[str, Any]:
        """配置 Ollama"""
        print("\n" + "-" * 30)
        print("🔧 Ollama 本地模型配置")
        print("-" * 30)

        base_url = self._input("\nOllama 服务地址", "http://localhost:11434")

        print("\n常用模型（需要提前下载）:")
        print("  - llama2")
        print("  - qwen2.5:7b")
        print("  - deepseek-r1:7b")
        model = self._input("模型名称", "llama2")

        return {
            "ollama": {
                "base_url": base_url,
                "model": model,
            }
        }

    def _step_notification(self) -> bool:
        """步骤3: 通知配置"""
        print("\n" + "-" * 50)
        print("📧 步骤 3/5: 通知配置")
        print("-" * 50)

        methods = self._input_choice(
            "请选择通知方式:", self.NOTIFICATION_METHODS, allow_multiple=False
        )
        method = methods[0]

        if method == "none":
            self.config["notification"] = {"enabled": False}
            print("\n✅ 通知功能已禁用")
            return True

        notification_config: Dict[str, Any] = {
            "enabled": True,
            "method": method,
        }

        if method == "email":
            notification_config["email"] = self._config_email()
        elif method == "webhook":
            notification_config["webhook"] = self._config_webhook()

        self.config["notification"] = notification_config
        print("\n✅ 通知配置完成")
        return True

    def _config_email(self) -> Dict[str, Any]:
        """配置邮件"""
        print("\n" + "-" * 30)
        print("📬 邮件配置")
        print("-" * 30)

        print("\n常用 SMTP 服务器:")
        print("  - Gmail: smtp.gmail.com")
        print("  - QQ邮箱: smtp.qq.com")
        print("  - 163邮箱: smtp.163.com")
        print("  - Outlook: smtp-mail.outlook.com")

        smtp_server = self._input("SMTP 服务器", "smtp.gmail.com")
        smtp_port = self._input("SMTP 端口", "587")

        try:
            smtp_port = int(smtp_port)
        except ValueError:
            smtp_port = 587

        sender = self._input("发件人邮箱", "")
        if not sender:
            print("⚠️  未提供发件人邮箱，请稍后在配置文件中填写")
            sender = "your-email@example.com"

        print("\n提示: Gmail 需要使用应用专用密码")
        print("      QQ/163邮箱 需要使用授权码")
        password = self._input("邮箱密码/授权码", "")
        if not password:
            print("⚠️  未提供密码，请稍后在配置文件中填写")
            password = "your-password-here"

        print("\n收件人邮箱（多个用逗号分隔）")
        recipients_str = self._input("收件人", sender)
        recipients = [
            r.strip() for r in recipients_str.replace("，", ",").split(",") if r.strip()
        ]

        return {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender": sender,
            "password": password,
            "recipients": recipients,
        }

    def _config_webhook(self) -> Dict[str, Any]:
        """配置 Webhook"""
        print("\n" + "-" * 30)
        print("🔗 Webhook 配置")
        print("-" * 30)

        url = self._input("\nWebhook URL", "")
        if not url:
            print("⚠️  未提供 Webhook URL，请稍后在配置文件中填写")
            url = "https://your-webhook-url.com/arxiv"

        method = self._input("HTTP 方法", "POST")

        return {
            "url": url,
            "method": method.upper(),
        }

    def _step_storage(self) -> bool:
        """步骤4: 存储配置"""
        print("\n" + "-" * 50)
        print("💾 步骤 4/5: 存储配置")
        print("-" * 50)

        data_dir = self._input("\n数据保存路径", "./data/papers")

        print("\n保存格式:")
        print("  1. json - JSON 格式")
        print("  2. csv - CSV 格式")
        print("  3. both - 同时保存两种格式")
        format_choice = self._input("保存格式", "both")
        if format_choice not in ("json", "csv", "both"):
            format_choice = "both"

        download_pdf = self._input_yes_no("是否下载论文 PDF（会增加时间和存储）", False)

        cache_enabled = self._input_yes_no(
            "是否启用缓存（推荐，可减少 API 成本）", True
        )

        auto_cleanup = self._input_yes_no(
            "邮件发送成功后是否自动删除本地文件（定时任务推荐启用）", False
        )

        self.config["storage"] = {
            "data_dir": data_dir,
            "format": format_choice,
            "download_pdf": download_pdf,
            "pdf_dir": "./data/pdfs",
            "cache_enabled": cache_enabled,
            "cache_file": "./data/papers/cache.json",
            "cache_max_items": 5000,
            "skip_processed": cache_enabled,
            "auto_cleanup": auto_cleanup,
        }

        print("\n✅ 存储配置完成")
        return True

    def _step_schedule(self) -> bool:
        """步骤5: 定时任务配置"""
        print("\n" + "-" * 50)
        print("⏰ 步骤 5/5: 定时任务配置")
        print("-" * 50)

        print("\n提示: 推荐使用系统 crontab 替代内置定时任务")
        enable_schedule = self._input_yes_no("是否启用内置定时任务", False)

        if enable_schedule:
            schedule_time = self._input("每天执行时间 (HH:MM)", "09:00")
            run_on_start = self._input_yes_no("启动时是否立即执行一次", False)
            self.config["schedule"] = {
                "enabled": True,
                "time": schedule_time,
                "run_on_start": run_on_start,
            }
        else:
            self.config["schedule"] = {
                "enabled": False,
                "time": "09:00",
            }

        print("\n✅ 定时任务配置完成")
        return True

    def _confirm_and_save(self) -> Optional[Dict[str, Any]]:
        """确认并保存配置"""
        print("\n" + "=" * 60)
        print("📋 配置预览")
        print("=" * 60)

        # 添加日志配置
        self.config["logging"] = {
            "level": "INFO",
            "file": "./logs/arxiv_scraper.log",
            "console": True,
            "max_size": 10,
            "backup_count": 5,
        }

        # 打印配置预览
        preview = yaml.dump(self.config, default_flow_style=False, allow_unicode=True)
        print(preview)

        print("=" * 60)

        if not self._input_yes_no("\n确认保存以上配置", True):
            print("\n⚠️  配置未保存")
            return None

        return self.config


def run_config_wizard() -> Optional[Dict[str, Any]]:
    """运行配置向导并返回配置"""
    wizard = ConfigWizard()
    return wizard.run()


def save_config(config: Dict[str, Any], path: str = "config.yaml") -> bool:
    """保存配置到文件"""
    try:
        # 备份现有配置
        if os.path.exists(path):
            backup_path = f"{path}.backup"
            import shutil

            shutil.copy(path, backup_path)
            print(f"\n💾 已备份现有配置到: {backup_path}")

        with open(path, "w", encoding="utf-8") as f:
            # 添加文件头注释
            f.write("# =====================================================\n")
            f.write("# ArXiv 论文抓取工具 - 配置文件\n")
            f.write("# 由交互式配置向导生成\n")
            f.write("# =====================================================\n\n")
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        print(f"\n✅ 配置已保存到: {path}")
        return True

    except Exception as e:
        print(f"\n❌ 保存配置失败: {str(e)}")
        return False


if __name__ == "__main__":
    config = run_config_wizard()
    if config:
        save_config(config)
