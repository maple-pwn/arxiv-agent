"""
配置管理模块
负责加载、验证和管理配置文件
"""

import os
import yaml
import logging
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'arxiv': {
            'keywords': ['machine learning'],
            'categories': [],
            'max_results': 50,
            'sort_by': 'submittedDate',
            'sort_order': 'descending'
        },
        'schedule': {
            'enabled': False,
            'time': '09:00'
        },
        'storage': {
            'data_dir': './data/papers',
            'format': 'both',
            'download_pdf': False,
            'pdf_dir': './data/pdfs',
            'cache_enabled': True,
            'cache_file': './data/papers/cache.json',
            'cache_max_items': 5000,
            'skip_processed': False
        },
        'logging': {
            'level': 'INFO',
            'file': './logs/arxiv_scraper.log',
            'console': True,
            'max_size': 10,
            'backup_count': 5
        },
        'notification': {
            'enabled': False,
            'method': 'email'
        }
    }

    def __init__(self, config_path: str = 'config.yaml'):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            配置字典
        """
        if not os.path.exists(self.config_path):
            self.logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)

            if user_config is None:
                self.logger.warning("配置文件为空，使用默认配置")
                return self.DEFAULT_CONFIG.copy()

            # 合并用户配置和默认配置
            config = self._merge_config(self.DEFAULT_CONFIG, user_config)
            self.logger.info(f"成功加载配置文件: {self.config_path}")

            # 验证配置
            self._validate_config(config)

            return config

        except yaml.YAMLError as e:
            self.logger.error(f"解析配置文件失败: {str(e)}")
            self.logger.warning("使用默认配置")
            return self.DEFAULT_CONFIG.copy()

        except Exception as e:
            self.logger.error(f"加载配置文件时出错: {str(e)}")
            self.logger.warning("使用默认配置")
            return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归合并配置字典

        Args:
            default: 默认配置
            user: 用户配置

        Returns:
            合并后的配置
        """
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        验证配置的有效性

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置无效时抛出
        """
        # 验证 ArXiv 配置
        arxiv_config = config.get('arxiv', {})

        max_results = arxiv_config.get('max_results', 50)
        if not isinstance(max_results, int) or max_results <= 0:
            raise ValueError(f"max_results 必须是正整数，当前值: {max_results}")

        sort_by = arxiv_config.get('sort_by', 'submittedDate')
        if sort_by not in ['submittedDate', 'lastUpdatedDate', 'relevance']:
            raise ValueError(f"无效的 sort_by 值: {sort_by}")

        sort_order = arxiv_config.get('sort_order', 'descending')
        if sort_order not in ['descending', 'ascending']:
            raise ValueError(f"无效的 sort_order 值: {sort_order}")

        # 验证存储配置
        storage_config = config.get('storage', {})

        save_format = storage_config.get('format', 'both')
        if save_format not in ['json', 'csv', 'both']:
            raise ValueError(f"无效的保存格式: {save_format}")

        # 验证日志配置
        logging_config = config.get('logging', {})

        log_level = logging_config.get('level', 'INFO')
        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError(f"无效的日志级别: {log_level}")

        self.logger.debug("配置验证通过")

    def get(self, key: str = None, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键（支持点号分隔的路径，如 'arxiv.max_results'）
            default: 默认值

        Returns:
            配置值
        """
        if key is None:
            return self.config

        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值（仅在内存中，不写入文件）

        Args:
            key: 配置键（支持点号分隔的路径）
            value: 配置值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: str = None) -> None:
        """
        保存配置到文件

        Args:
            path: 保存路径，默认使用加载时的路径
        """
        save_path = path or self.config_path

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"配置已保存到: {save_path}")

        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")
            raise

    def reload(self) -> None:
        """重新加载配置文件"""
        self.config = self._load_config()
        self.logger.info("配置已重新加载")


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    便捷函数：加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    manager = ConfigManager(config_path)
    return manager.config
