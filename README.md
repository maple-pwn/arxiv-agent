# ArXiv 论文自动抓取工具

一个自动化的 ArXiv 论文抓取工具，支持 AI 驱动的论文总结、翻译和关键洞察提取，并可自动生成邮件报告。

## 特性

- 🔍 **智能搜索**：支持关键词和分类筛选
- 🤖 **AI 分析**：集成 OpenAI/Claude/Ollama，自动总结和翻译
- 💡 **关键洞察**：AI 提取论文核心创新点
- 📧 **邮件推送**：自动生成 Markdown 报告并发送
- ⏰ **定时任务**：支持定时自动抓取
- 🐳 **Docker 支持**：一键部署，开箱即用

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd paper-agent

# 2. 配置
cp config.yaml.template config.yaml
# 编辑 config.yaml 填入你的配置

# 3. 启动
docker-compose up -d
```

### 本地部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp config.yaml.template config.yaml
# 编辑 config.yaml

# 3. 运行
python main.py
```

## 配置说明

### 基本配置

```yaml
arxiv:
  keywords:
    - "machine learning"
    - "deep learning"
  categories:
    - "cs.AI"
    - "cs.LG"
  max_results: 50
```

### AI 配置

#### 使用 OpenAI 或兼容 API

```yaml
ai:
  enabled: true
  provider: "openai"
  enable_summary: true       # 论文总结
  enable_translation: true   # 摘要翻译
  enable_insights: true      # 关键洞察
  send_markdown_report: true # 邮件报告

  openai:
    api_key: "your-api-key"
    model: "gpt-3.5-turbo"
    base_url: "https://api.openai.com/v1"
```

#### 使用硅基流动 API

```yaml
ai:
  enabled: true
  provider: "openai"
  openai:
    api_key: "your-siliconflow-api-key"
    model: "deepseek-ai/DeepSeek-V3"
    base_url: "https://api.siliconflow.cn/v1"  # 注意不要包含 /chat/completions
```

#### 使用 Claude

```yaml
ai:
  provider: "anthropic"
  anthropic:
    api_key: "your-anthropic-api-key"
    model: "claude-3-5-sonnet-20241022"
```

#### 使用本地 Ollama

```yaml
ai:
  provider: "ollama"
  ollama:
    model: "llama2"
    base_url: "http://localhost:11434"
```

### 邮件配置

```yaml
notification:
  enabled: true
  method: "email"
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your-email@gmail.com"
    password: "your-app-password"
    recipients:
      - "recipient@example.com"
```

### 定时任务

```yaml
schedule:
  enabled: true
  time: "09:00"  # 每天09:00执行
```

### 自动清理配置

```yaml
storage:
  # 邮件发送后自动删除本地文件（包括 papers 和 reports）
  auto_cleanup: true
```

**说明**：
- 启用后，邮件发送成功将自动删除本地的 papers 文件（JSON/CSV）和 reports 文件（Markdown）
- 如果邮件发送失败，文件将保留在本地
- 默认值为 `false`，需要手动启用
- 适合定时任务场景，避免磁盘空间占用

## 输出说明

### JSON 格式

保存在 `./data/papers/` 目录，包含：
- 论文基本信息
- AI 总结
- 中文翻译
- 关键洞察

### Markdown 报告

保存在 `./data/reports/` 目录，包含：
- 📋 基本信息（标题、作者、ArXiv ID、PDF链接）
- 💡 关键洞察（3-5个核心创新点）
- 📝 原文摘要
- 🌐 中文翻译
- 🤖 AI 智能总结（核心观点、研究方法、关键结果、应用价值）

### 邮件通知

自动发送 Markdown 报告到指定邮箱，包含所有论文的完整分析。

## 项目结构

```
paper-agent/
├── config.yaml          # 配置文件
├── main.py              # 主程序入口
├── requirements.txt     # Python依赖
├── Dockerfile           # Docker镜像定义
├── docker-compose.yml   # Docker Compose配置
├── src/                 # 源代码
│   ├── arxiv_scraper.py    # 论文抓取
│   ├── ai_service.py       # AI服务（总结/翻译/洞察）
│   ├── markdown_generator.py  # Markdown生成
│   └── utils.py            # 工具函数
├── data/                # 数据目录
│   ├── papers/          # 论文JSON/CSV
│   └── reports/         # Markdown报告
└── logs/                # 日志文件
```

## 使用示例

### 单次运行

```bash
python main.py
```

### 定时任务模式

编辑 `config.yaml` 启用定时任务：
```yaml
schedule:
  enabled: true
  time: "09:00"
```

然后运行：
```bash
python main.py
```

## 常见问题

### 1. OpenAI API 调用失败

检查：
- API key 是否正确
- base_url 是否正确（不要包含 `/chat/completions`）
- 网络连接是否正常

### 2. 邮件发送失败

检查：
- SMTP 配置是否正确
- Gmail 需使用应用专用密码（不是登录密码）
- 防火墙是否允许 SMTP 端口

### 3. Docker 部署问题

```bash
# 查看日志
docker-compose logs -f

# 重新构建
docker-compose build --no-cache

# 重启服务
docker-compose restart
```

## API 成本估算

以 OpenAI GPT-3.5-turbo 为例（每篇论文）：
- 总结：约 500 tokens
- 翻译：约 300 tokens
- 洞察提取：约 200 tokens
- **总计**：约 1000 tokens ≈ \$0.002

50篇论文 ≈ \$0.10（约0.7元）

使用硅基流动 API 可显著降低成本（DeepSeek-V3 更便宜）。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
