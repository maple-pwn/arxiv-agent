"""
配置加载模块
支持从环境变量和YAML文件加载配置
优先级：环境变量 > YAML文件
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = './config.yaml'):
        """
        初始化配置加载器

        Args:
            config_path: YAML配置文件路径
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)

    def load(self) -> Dict[str, Any]:
        """
        加载配置

        Returns:
            配置字典
        """
        # 首先从YAML文件加载
        config = self._load_from_yaml()

        # 然后从环境变量覆盖
        config = self._override_from_env(config)

        return config

    def _load_from_yaml(self) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        if not os.path.exists(self.config_path):
            self.logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.info(f"已从 {self.config_path} 加载配置")
                return config or {}
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            return self._get_default_config()

    def _override_from_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """从环境变量覆盖配置"""
        # ArXiv配置
        if 'arxiv' not in config:
            config['arxiv'] = {}

        if os.getenv('ARXIV_KEYWORDS'):
            config['arxiv']['keywords'] = os.getenv('ARXIV_KEYWORDS').split(',')

        if os.getenv('ARXIV_CATEGORIES'):
            config['arxiv']['categories'] = os.getenv('ARXIV_CATEGORIES').split(',')

        if os.getenv('ARXIV_MAX_RESULTS'):
            config['arxiv']['max_results'] = int(os.getenv('ARXIV_MAX_RESULTS'))

        if os.getenv('ARXIV_SORT_BY'):
            config['arxiv']['sort_by'] = os.getenv('ARXIV_SORT_BY')

        if os.getenv('ARXIV_SORT_ORDER'):
            config['arxiv']['sort_order'] = os.getenv('ARXIV_SORT_ORDER')

        # AI配置
        if 'ai' not in config:
            config['ai'] = {}

        if os.getenv('AI_ENABLED'):
            config['ai']['enabled'] = os.getenv('AI_ENABLED').lower() == 'true'

        if os.getenv('AI_PROVIDER'):
            config['ai']['provider'] = os.getenv('AI_PROVIDER')

        # OpenAI配置
        if os.getenv('OPENAI_API_KEY'):
            if 'openai' not in config['ai']:
                config['ai']['openai'] = {}
            config['ai']['openai']['api_key'] = os.getenv('OPENAI_API_KEY')

        if os.getenv('OPENAI_BASE_URL'):
            if 'openai' not in config['ai']:
                config['ai']['openai'] = {}
            config['ai']['openai']['base_url'] = os.getenv('OPENAI_BASE_URL')

        if os.getenv('OPENAI_MODEL'):
            if 'openai' not in config['ai']:
                config['ai']['openai'] = {}
            config['ai']['openai']['model'] = os.getenv('OPENAI_MODEL')

        # Anthropic配置
        if os.getenv('ANTHROPIC_API_KEY'):
            if 'anthropic' not in config['ai']:
                config['ai']['anthropic'] = {}
            config['ai']['anthropic']['api_key'] = os.getenv('ANTHROPIC_API_KEY')

        if os.getenv('ANTHROPIC_MODEL'):
            if 'anthropic' not in config['ai']:
                config['ai']['anthropic'] = {}
            config['ai']['anthropic']['model'] = os.getenv('ANTHROPIC_MODEL')

        # 通知配置
        if 'notification' not in config:
            config['notification'] = {}

        if os.getenv('NOTIFICATION_ENABLED'):
            config['notification']['enabled'] = os.getenv('NOTIFICATION_ENABLED').lower() == 'true'

        if os.getenv('NOTIFICATION_METHOD'):
            config['notification']['method'] = os.getenv('NOTIFICATION_METHOD')

        # 邮件配置
        if os.getenv('EMAIL_SMTP_SERVER'):
            if 'email' not in config['notification']:
                config['notification']['email'] = {}
            config['notification']['email']['smtp_server'] = os.getenv('EMAIL_SMTP_SERVER')

        if os.getenv('EMAIL_SMTP_PORT'):
            if 'email' not in config['notification']:
                config['notification']['email'] = {}
            config['notification']['email']['smtp_port'] = int(os.getenv('EMAIL_SMTP_PORT'))

        if os.getenv('EMAIL_SENDER'):
            if 'email' not in config['notification']:
                config['notification']['email'] = {}
            config['notification']['email']['sender'] = os.getenv('EMAIL_SENDER')

        if os.getenv('EMAIL_PASSWORD'):
            if 'email' not in config['notification']:
                config['notification']['email'] = {}
            config['notification']['email']['password'] = os.getenv('EMAIL_PASSWORD')

        if os.getenv('EMAIL_RECIPIENTS'):
            if 'email' not in config['notification']:
                config['notification']['email'] = {}
            config['notification']['email']['recipients'] = os.getenv('EMAIL_RECIPIENTS').split(',')

        # Webhook配置
        if os.getenv('WEBHOOK_URL'):
            if 'webhook' not in config['notification']:
                config['notification']['webhook'] = {}
            config['notification']['webhook']['url'] = os.getenv('WEBHOOK_URL')

        if os.getenv('WEBHOOK_METHOD'):
            if 'webhook' not in config['notification']:
                config['notification']['webhook'] = {}
            config['notification']['webhook']['method'] = os.getenv('WEBHOOK_METHOD')

        # 存储配置
        if 'storage' not in config:
            config['storage'] = {}

        if os.getenv('STORAGE_AUTO_CLEANUP'):
            config['storage']['auto_cleanup'] = os.getenv('STORAGE_AUTO_CLEANUP').lower() == 'true'

        if os.getenv('STORAGE_FORMAT'):
            config['storage']['format'] = os.getenv('STORAGE_FORMAT')

        self.logger.info("已从环境变量覆盖配置")
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'arxiv': {
                'keywords': ['machine learning', 'deep learning'],
                'categories': ['cs.AI', 'cs.LG'],
                'max_results': 10,
                'sort_by': 'submittedDate',
                'sort_order': 'descending'
            },
            'storage': {
                'data_dir': './data/papers',
                'format': 'both',
                'download_pdf': False,
                'auto_cleanup': False
            },
            'ai': {
                'enabled': False,
                'provider': 'openai',
                'enable_summary': True,
                'enable_translation': True,
                'enable_insights': True,
                'send_markdown_report': False
            },
            'notification': {
                'enabled': False,
                'method': 'email'
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/arxiv_scraper.log',
                'console': True
            }
        }


def load_config(config_path: str = './config.yaml') -> Dict[str, Any]:
    """
    加载配置（便捷函数）

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    loader = ConfigLoader(config_path)
    return loader.load()