# ArXiv 论文自动抓取工具

> 🚀 一个功能强大的 ArXiv 论文自动抓取工具，集成 AI 智能分析，支持自动总结、翻译、洞察提取和邮件推送。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ 特性

- 🔍 **智能搜索**：支持关键词、分类、相关度评分等多维度筛选
- 🤖 **AI 分析**：集成 OpenAI/Claude/Ollama，提供结构化总结
- 🎯 **智能筛选**：AI 自动过滤不相关论文，节省处理成本
- 💡 **关键洞察**：AI 自动提取论文核心创新点和技术亮点
- 📧 **灵活推送**：支持邮件（带重试）和 Webhook 两种推送方式
- ⏰ **定时任务**：支持 Cron 式定时自动抓取
- 🐳 **Docker 支持**：一键部署，开箱即用
- 🎨 **自定义Prompt**：可自定义AI分析维度和输出格式
- 🔄 **配置迁移**：智能合并配置，安全更新不丢失数据

## 快速开始

### 本地部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化配置
python main.py --init
# 根据提示编辑 config.yaml

# 3. 运行
python main.py
```

### Docker 部署

```bash
# 1. 配置
cp config.yaml.template config.yaml
# 编辑 config.yaml 填入你的配置

# 2. 启动
docker-compose up -d
```

## 核心配置

配置文件 `config.yaml` 包含所有功能设置，以下是关键配置项：

### 1. 搜索配置

```yaml
arxiv:
  # 搜索关键词（宽泛搜索，多捞一些论文）
  keywords:
    - "machine learning"
    - "deep learning"

  # 分类筛选（可选）
  categories:
    - "cs.AI"
    - "cs.LG"

  # 抓取数量
  max_results: 50
```

### 2. AI 配置

```yaml
ai:
  enabled: true
  provider: "openai"  # 支持 openai/anthropic/ollama

  # OpenAI 配置
  openai:
    api_key: "your-api-key-here"
    model: "gpt-3.5-turbo"
    base_url: "https://api.openai.com/v1"

  # AI 功能开关
  enable_summary: true       # 4维度总结
  enable_translation: true   # 中文翻译
  enable_insights: true      # 关键洞察

  # AI 智能筛选（精准过滤，只保留相关论文）
  enable_filter: false
  filter_keywords: "游戏AI, 强化学习应用"  # 与arxiv.keywords不同，用于精准筛选
  filter_threshold: 0.7  # 置信度阈值（0.6-0.8推荐）
```

**关键词说明**：
- `arxiv.keywords`：用于 ArXiv 搜索，应该宽泛一些（如 "machine learning"）
- `ai.filter_keywords`：用于 AI 精准筛选，应该具体一些（如 "医学影像诊断"）

### 3. 通知配置

```yaml
notification:
  enabled: true
  method: "email"  # 或 "webhook"

  # 邮件配置
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your-email@gmail.com"
    password: "your-app-password"  # Gmail需要应用专用密码
    recipients:
      - "recipient@example.com"

# 要接收邮件报告，需要同时设置：
# 1. notification.enabled: true
# 2. notification.method: "email"
# 3. ai.send_markdown_report: true
```

**邮箱配置快速指南**：
- **Gmail**: [生成应用专用密码](https://myaccount.google.com/apppasswords)（需开启两步验证）
- **QQ邮箱**: 设置 → 账户 → 开启SMTP → 生成授权码
- **163邮箱**: 设置 → 客户端授权密码

### 4. 定时任务

```bash
# 方式1：程序内置定时任务
# config.yaml:
schedule:
  enabled: true
  time: "09:00"

python main.py  # 会在每天9点执行

# 方式2：系统crontab（推荐）
crontab -e
# 添加：0 9 * * * cd /path/to/paper-agent && python main.py
```

## 配置更新和迁移

项目更新后使用迁移工具安全更新配置：

```bash
# 预览变更
python config_migration.py --dry-run

# 执行迁移（自动备份）
python config_migration.py

# 验证配置
python config_migration.py --validate
```

或在初始化时选择"智能合并"：
```bash
python main.py --init
# 选择：1. 智能合并（推荐）
```

## 详细文档

- 📖 **完整配置说明**：查看 [config.yaml.template](config.yaml.template)，包含所有配置项的详细说明和示例
- 🎨 **自定义 Prompt**：查看 [docs/CUSTOM_PROMPTS.md](docs/CUSTOM_PROMPTS.md)，自定义 AI 分析维度
- 📝 **功能更新日志**：查看 [docs/UPDATES.md](docs/UPDATES.md)，了解最新功能和改进

## 项目结构

```
paper-agent/
├── config.yaml              # 配置文件
├── config_migration.py      # 配置迁移工具
├── main.py                  # 主程序入口
├── requirements.txt         # Python依赖
├── src/                     # 源代码
│   ├── arxiv_scraper.py    # 论文抓取 + AI筛选
│   ├── ai_service.py       # AI服务（总结/翻译/洞察）
│   ├── markdown_generator.py  # Markdown报告生成
│   └── utils.py            # 工具函数
├── prompts/                 # AI Prompt模板
│   └── prompts.yaml        # 可自定义
├── data/                    # 数据目录
│   ├── papers/             # 论文JSON/CSV
│   └── reports/            # Markdown报告
└── logs/                    # 日志文件
```

## 使用示例

```bash
# 单次运行
python main.py

# 定时任务模式（程序常驻）
python main.py --schedule

# 初始化配置
python main.py --init

# 配置迁移
python config_migration.py
python config_migration.py --dry-run    # 预览
python config_migration.py --validate   # 验证
```

## 生产环境配置示例

```yaml
arxiv:
  keywords: ["machine learning", "deep learning"]
  categories: ["cs.AI", "cs.LG"]
  max_results: 20

storage:
  auto_cleanup: true  # 邮件发送后自动清理

ai:
  enabled: true
  provider: "openai"
  enable_filter: true
  filter_keywords: "医学影像, 疾病诊断"  # 精准筛选
  filter_threshold: 0.7
  send_markdown_report: true

  openai:
    api_key: "sk-xxxxxxxx"
    model: "gpt-3.5-turbo"
    base_url: "https://api.siliconflow.cn/v1"  # 可用国内API

notification:
  enabled: true
  method: "email"
  email:
    smtp_server: "smtp.qq.com"
    smtp_port: 587
    sender: "your@qq.com"
    password: "your-auth-code"
    recipients: ["recipient@example.com"]

schedule:
  enabled: true
  time: "09:00"
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！