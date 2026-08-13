"""配置加载与路径常量。"""
from __future__ import annotations

import copy
import os

import yaml

DATA_DIR = "data"
DOCS_DIR = "docs"

DEFAULTS: dict = {
    "categories": {
        "cs.RO": "机器人学",
        "cs.CV": "计算机视觉",
        "cs.AI": "人工智能",
        "cs.CL": "计算语言学",
    },
    "keywords": [],
    "llm": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "timeout": 120,
        "max_retries": 3,
        "concurrency": 8,
    },
    "translate": {
        "only_favorites": False,
    },
    "site": {
        "title": "arXiv Papers",
        "subtitle": "Daily Research Digest",
        "base_url": "",
        "timezone": "Asia/Shanghai",
    },
    "analytics": "",
}


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_config(path: str = "config.yaml") -> dict:
    """加载 YAML 配置并叠加到默认值上。"""
    config = copy.deepcopy(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            user = yaml.safe_load(fh) or {}
        # categories / keywords 是用户自定义的完整集合，应整体替换默认值，
        # 而不是与默认值做字典合并（否则默认分类会一直泄漏进来）。
        for key in ("categories", "keywords"):
            if key in user:
                config[key] = copy.deepcopy(user[key])
                user.pop(key)
        _deep_merge(config, user)
    return config


def get_api_key(config: dict) -> str | None:
    """从环境变量读取 LLM API key。"""
    env_name = config["llm"].get("api_key_env", "DEEPSEEK_API_KEY")
    return os.environ.get(env_name)


def category_name(config: dict, code: str) -> str:
    """返回分类的中文名，未配置时回退为分类代码本身。"""
    return config["categories"].get(code, code)
