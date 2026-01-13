# ArXiv 论文自动抓取工具

> 🚀 一个功能强大的 ArXiv 论文自动抓取工具，集成 AI 智能分析，支持自动总结、翻译、洞察提取和邮件推送。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ 特性

- 🔍 **智能搜索**：支持关键词、分类、时间范围等多维度筛选
- 🤖 **AI 分析**：集成 OpenAI/Claude/Ollama，提供结构化总结
- 💡 **关键洞察**：AI 自动提取论文核心创新点和技术亮点
- 📧 **灵活推送**：支持邮件（带重试）和 Webhook 两种推送方式
- ⏰ **定时任务**：支持 Cron 式定时自动抓取
- 🐳 **Docker 支持**：一键部署，开箱即用
- 🎨 **自定义Prompt**：可自定义AI分析维度和输出格式
- 🧹 **自动清理**：邮件发送成功后自动删除本地文件

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

## 📋 详细配置说明

配置文件使用 YAML 格式，所有配置项都有详细说明。建议先复制 `config.yaml.template` 为 `config.yaml`，然后根据需要修改。

### 1. ArXiv 论文搜索配置

控制如何从 ArXiv 搜索和筛选论文。

```yaml
arxiv:
  # 搜索关键词（多个关键词之间是OR关系）
  keywords:
    - "machine learning"
    - "deep learning"
    - "neural network"

  # ArXiv 分类代码（多个分类之间是OR关系）
  # 常用分类：cs.AI (人工智能), cs.LG (机器学习), cs.CV (计算机视觉), cs.CL (自然语言处理)
  # 完整列表：https://arxiv.org/category_taxonomy
  categories:
    - "cs.AI"
    - "cs.LG"

  # 每次抓取的最大论文数量
  max_results: 50

  # 排序方式：submittedDate (提交日期), lastUpdatedDate (最后更新日期), relevance (相关性)
  sort_by: "submittedDate"

  # 排序顺序：descending (降序，最新的在前), ascending (升序，最旧的在前)
  sort_order: "descending"
```

**配置技巧**：
- **关键词搜索**：使用英文关键词，支持引号包裹精确匹配
- **分类筛选**：推荐使用分类+关键词组合，提高结果精准度
- **数量控制**：建议根据AI处理成本控制 `max_results`（每篇约消耗1000 tokens）

### 2. 存储配置

控制论文数据的保存方式和位置。

```yaml
storage:
  # 数据保存目录
  data_dir: "./data/papers"

  # 保存格式：json, csv, both
  format: "both"

  # 是否下载 PDF（会显著增加运行时间和存储空间）
  download_pdf: false

  # PDF 保存目录（仅当 download_pdf 为 true 时有效）
  pdf_dir: "./data/pdfs"

  # 邮件发送成功后自动删除本地文件
  # 启用后会删除 papers 文件（JSON/CSV）和 reports 文件（Markdown）
  auto_cleanup: true
```

**配置建议**：
- **download_pdf**: 除非特别需要，建议设为 `false`（可通过 PDF 链接在线查看）
- **auto_cleanup**: 定时任务场景建议启用，避免磁盘占满

### 3. AI 功能配置

配置 AI 服务提供商和功能开关。

#### 3.1 基础配置

```yaml
ai:
  # 是否启用 AI 功能（关闭后仅抓取原始数据）
  enabled: true

  # AI 服务提供商：openai, anthropic (Claude), ollama
  provider: "openai"

  # 是否启用论文总结（4个维度：核心观点、研究方法、关键结果、应用价值）
  enable_summary: true

  # 是否翻译摘要为中文
  enable_translation: true

  # 是否提取关键洞察（3-5个核心创新点）
  enable_insights: true

  # ========== AI 智能筛选（新功能） ==========
  # 是否启用 AI 智能筛选（在处理前过滤不相关论文）
  enable_filter: true

  # AI 筛选关键词（用于判断论文相关性）
  # 示例：" 强化学习在游戏中的应用, 多智能体协同, 深度强化学习算法优化"
  filter_keywords: "强化学习应用, 游戏AI, 多智能体系统"

  # AI 筛选置信度阈值（0.0-1.0，只保留置信度高于此值的论文）
  # 建议值：0.6-0.8，越高越严格
  # 0.6 - 宽松（保留较多论文）
  # 0.7 - 平衡（推荐）
  # 0.8 - 严格（只保留高度相关论文）
  filter_threshold: 0.7

  # 是否生成并发送 Markdown 报告
  send_markdown_report: true

  # Markdown 报告保存目录
  markdown_dir: "./data/reports"
```

**AI 智能筛选说明**：
- **工作原理**：在论文抓取后、AI 处理前，先通过 AI 判断论文与您指定的关键词的相关性
- **优势**：节省 AI 成本（只处理相关论文）+ 提升报告质量（过滤无关内容）
- **使用场景**：
  - ArXiv 搜索关键词太宽泛，返回很多不相关论文
  - 希望聚焦特定研究方向或应用场景
  - 需要降低 AI 处理成本

**配置示例**：
```yaml
# 场景1：只关注强化学习在游戏中的应用
filter_keywords: "游戏AI, 强化学习在游戏中的应用, 游戏智能体训练"
filter_threshold: 0.75

# 场景2：关注医疗AI的多个方向
filter_keywords: "医学影像诊断, 疾病预测, 药物发现, AI辅助诊疗"
filter_threshold: 0.65

# 场景3：严格筛选特定算法
filter_keywords: "Transformer架构改进, 注意力机制优化"
filter_threshold: 0.8
```

#### 3.2 OpenAI 配置（推荐）

```yaml
ai:
  provider: "openai"
  openai:
    # OpenAI API 密钥
    api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # 模型选择
    # - gpt-3.5-turbo: 便宜，速度快，适合大批量
    # - gpt-4o-mini: 性价比高
    # - gpt-4o: 质量最高，价格较贵
    model: "gpt-3.5-turbo"

    # API 端点（官方或第三方兼容服务）
    base_url: "https://api.openai.com/v1"

    # 单次请求最大token数
    max_tokens: 1000

    # 温度参数（0-2），值越高越随机
    temperature: 0.7
```

#### 3.3 硅基流动配置（国内推荐）

硅基流动提供国内可访问的 OpenAI 兼容 API，支持 DeepSeek-V3 等模型。

```yaml
ai:
  provider: "openai"  # 使用 OpenAI 兼容接口
  openai:
    api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 在 https://siliconflow.cn 获取
    model: "deepseek-ai/DeepSeek-V3"  # 或 "Qwen/Qwen2.5-7B-Instruct"
    base_url: "https://api.siliconflow.cn/v1"  # 注意：不要加 /chat/completions
```

**优势**：
- ✅ 国内直连，无需魔法
- ✅ DeepSeek-V3 成本极低（约为 GPT-3.5 的 1/10）
- ✅ 完全兼容 OpenAI API

**获取 API Key**：
1. 访问 [https://siliconflow.cn](https://siliconflow.cn)
2. 注册并登录
3. 在 API Keys 页面创建密钥
4. 复制密钥到配置文件

#### 3.4 Claude 配置

```yaml
ai:
  provider: "anthropic"
  anthropic:
    api_key: "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    model: "claude-3-5-sonnet-20241022"  # 或 "claude-3-5-haiku-20241022"
    base_url: "https://api.anthropic.com/v1"
    max_tokens: 1000
    temperature: 0.7
```

**模型选择**：
- **claude-3-5-sonnet**: 质量最高，适合学术分析
- **claude-3-5-haiku**: 速度快，成本低

#### 3.5 Ollama 本地配置

使用本地运行的 Ollama，完全免费，无需 API 密钥。

```yaml
ai:
  provider: "ollama"
  ollama:
    model: "llama2"  # 或 "qwen2.5:7b", "deepseek-r1:7b"
    base_url: "http://localhost:11434"
```

**前置要求**：
1. 安装 Ollama：https://ollama.ai
2. 拉取模型：`ollama pull llama2`
3. 启动服务：`ollama serve`

**优势**：完全免费，数据本地处理，隐私性好
**劣势**：需要本地算力，质量不如云端大模型

### 4. 通知配置

配置如何接收论文报告。

#### 4.1 邮件通知（带重试机制）

```yaml
notification:
  # 是否启用通知
  enabled: true

  # 通知方式：email 或 webhook
  method: "email"

  # 邮件配置
  email:
    # SMTP 服务器地址
    smtp_server: "smtp.gmail.com"

    # SMTP 端口（一般是 587 或 465）
    smtp_port: 587

    # 发件人邮箱
    sender: "your-email@gmail.com"

    # 邮箱密码或应用专用密码
    password: "your-app-password"

    # 收件人列表（可以多个）
    recipients:
      - "recipient1@example.com"
      - "recipient2@example.com"
```

**重要说明**：

**Gmail 配置**：
1. 开启两步验证：https://myaccount.google.com/security
2. 生成应用专用密码：https://myaccount.google.com/apppasswords
3. 使用生成的16位密码（格式：xxxx xxxx xxxx xxxx）

**QQ 邮箱配置**：
```yaml
email:
  smtp_server: "smtp.qq.com"
  smtp_port: 587
  sender: "your-qq@qq.com"
  password: "授权码"  # 在QQ邮箱设置-账户中获取授权码
```

**163 邮箱配置**：
```yaml
email:
  smtp_server: "smtp.163.com"
  smtp_port: 465
  sender: "your-email@163.com"
  password: "授权码"  # 在邮箱设置中获取授权码
```

**重试机制**：邮件发送失败时会自动重试 3 次，每次间隔 5 秒。

#### 4.2 Webhook 通知（推荐）

如果邮件发送经常超时，建议改用 Webhook 方式。

```yaml
notification:
  enabled: true
  method: "webhook"

  webhook:
    # Webhook 接收地址
    url: "https://your-api.example.com/arxiv/report"

    # HTTP 方法
    method: "POST"
```

**Webhook 请求格式**：
```json
{
  "type": "arxiv_report",
  "timestamp": "20260113_120000",
  "paper_count": 5,
  "content": "# ArXiv 论文日报\n\n...",
  "format": "markdown"
}
```

**适用场景**：
- 企业微信/钉钉机器人
- Slack/Discord 通知
- 自建服务接收处理

### 5. 定时任务配置

配置自动执行时间。

```yaml
schedule:
  # 是否启用定时任务
  enabled: true

  # 执行时间（24小时制）
  time: "09:00"

  # 是否在启动时立即执行一次
  run_on_start: false
```

**使用方法**：
```bash
# 以定时任务模式启动（会一直运行）
python main.py --schedule

# 或者使用系统 crontab（Linux/Mac）
crontab -e
# 添加：0 9 * * * cd /path/to/paper-agent && python main.py
```

### 6. 日志配置

控制日志输出和存储。

```yaml
logging:
  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: "INFO"

  # 日志文件路径
  file: "./logs/arxiv_scraper.log"

  # 是否同时输出到控制台
  console: true

  # 日志文件最大大小（MB）
  max_size: 10

  # 保留的日志文件数量（日志轮转）
  backup_count: 5
```

**日志级别说明**：
- **DEBUG**: 详细调试信息（开发时使用）
- **INFO**: 一般信息（推荐）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

### 7. 自定义 Prompt（高级）

可以自定义 AI 分析的维度和输出格式，编辑 `prompts/prompts.yaml`：

```yaml
summarize:
  system: "你是一位专业的学术论文分析专家。"
  user_template: |
    请对以下论文进行分析：
    标题：{title}
    摘要：{summary}

    请从以下角度分析：
    1. 核心创新点
    2. 技术方法
    3. 实验结果
    4. 应用价值
```

详见：[Prompt 自定义指南](docs/CUSTOM_PROMPTS.md)

---

## 📝 完整配置示例

以下是一个生产环境的完整配置示例：

```yaml
# ArXiv 搜索配置
arxiv:
  keywords: ["machine learning", "deep learning", "transformer"]
  categories: ["cs.AI", "cs.LG", "cs.CL"]
  max_results: 20
  sort_by: "submittedDate"
  sort_order: "descending"

# 存储配置
storage:
  data_dir: "./data/papers"
  format: "both"
  download_pdf: false
  auto_cleanup: true

# AI 配置（使用硅基流动）
ai:
  enabled: true
  provider: "openai"
  enable_summary: true
  enable_translation: true
  enable_insights: true
  send_markdown_report: true
  markdown_dir: "./data/reports"

  openai:
    api_key: "sk-xxxxxxxx"
    model: "deepseek-ai/DeepSeek-V3"
    base_url: "https://api.siliconflow.cn/v1"

# 通知配置（使用 QQ 邮箱）
notification:
  enabled: true
  method: "email"

  email:
    smtp_server: "smtp.qq.com"
    smtp_port: 587
    sender: "your-qq@qq.com"
    password: "your-auth-code"
    recipients:
      - "recipient@example.com"

# 定时任务（每天早上9点）
schedule:
  enabled: true
  time: "09:00"
  run_on_start: false

# 日志配置
logging:
  level: "INFO"
  file: "./logs/arxiv_scraper.log"
  console: true
  max_size: 10
  backup_count: 5
```

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

## ❓ 常见问题与故障排查

### 1. OpenAI API 调用失败

**症状**：
```
AIServiceError: API 调用失败: Connection timeout
```

**可能原因及解决方案**：

#### 问题1：API Key 错误
```yaml
# ❌ 错误：API key 格式不对
api_key: "your-api-key"

# ✅ 正确：应该是 sk- 开头的真实密钥
api_key: "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 问题2：base_url 配置错误
```yaml
# ❌ 错误：包含了 /chat/completions
base_url: "https://api.openai.com/v1/chat/completions"

# ✅ 正确：只到 /v1
base_url: "https://api.openai.com/v1"
```

#### 问题3：网络连接问题
- **官方 OpenAI API**：需要科学上网
- **解决方案**：使用国内服务商（如硅基流动）
  ```yaml
  ai:
    provider: "openai"
    openai:
      api_key: "sk-xxxxxxxx"
      base_url: "https://api.siliconflow.cn/v1"
  ```

#### 问题4：配额不足
- 检查 OpenAI 账户余额
- 查看 API 使用限制

**调试技巧**：
```bash
# 查看详细日志
python main.py

# 检查日志文件
tail -f logs/arxiv_scraper.log
```

### 2. 邮件发送失败

**症状**：
```
[Errno 110] Connection timed out
邮件发送失败，已达到最大重试次数 (3)
```

**解决方案**：

#### 方案1：使用应用专用密码（Gmail）

1. 访问 https://myaccount.google.com/security
2. 开启两步验证
3. 生成应用专用密码：https://myaccount.google.com/apppasswords
4. 使用生成的16位密码：

```yaml
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender: "your-email@gmail.com"
  password: "abcd efgh ijkl mnop"  # 应用专用密码，带空格
```

#### 方案2：切换到QQ邮箱

QQ邮箱更稳定，推荐使用：

```yaml
email:
  smtp_server: "smtp.qq.com"
  smtp_port: 587  # 或 465（SSL）
  sender: "your-qq@qq.com"
  password: "授权码"  # 不是QQ密码！
```

**获取QQ邮箱授权码**：
1. 登录 QQ 邮箱
2. 设置 → 账户 → 开启 SMTP 服务
3. 生成授权码
4. 复制授权码到配置文件

#### 方案3：改用Webhook（最稳定）

如果邮件持续失败，建议使用 Webhook：

```yaml
notification:
  enabled: true
  method: "webhook"
  webhook:
    url: "https://your-webhook-url.com/arxiv"
    method: "POST"
```

**搭建简单的 Webhook 接收服务**：
```python
# webhook_server.py
from flask import Flask, request
app = Flask(__name__)

@app.route('/arxiv', methods=['POST'])
def receive_report():
    data = request.json
    content = data['content']
    # 保存到文件或发送到其他服务
    with open('report.md', 'w') as f:
        f.write(content)
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(port=5000)
```

### 3. 配置文件解析错误

**症状**：
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**原因**：YAML 格式错误

**常见错误**：

```yaml
# ❌ 错误：缩进不一致
ai:
  enabled: true
 provider: "openai"  # 缩进少了一个空格

# ✅ 正确：缩进对齐
ai:
  enabled: true
  provider: "openai"
```

```yaml
# ❌ 错误：冒号后没有空格
smtp_server:"smtp.gmail.com"

# ✅ 正确：冒号后要有空格
smtp_server: "smtp.gmail.com"
```

```yaml
# ❌ 错误：字符串包含特殊字符未加引号
password: xxx@123

# ✅ 正确：包含特殊字符要加引号
password: "xxx@123"
```

**验证配置文件**：
```bash
# 使用 Python 验证 YAML 语法
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### 4. 找不到论文

**症状**：
```
成功获取 0 篇论文
```

**可能原因**：

#### 原因1：关键词太精确
```yaml
# ❌ 太精确，可能找不到
keywords: ["very specific long tail keyword combination"]

# ✅ 使用常见术语
keywords: ["machine learning", "deep learning"]
```

#### 原因2：分类和关键词冲突
```yaml
# ❌ 医学关键词 + 计算机分类
keywords: ["cancer treatment"]
categories: ["cs.AI"]  # 不匹配

# ✅ 关键词和分类匹配
keywords: ["medical AI", "diagnosis"]
categories: ["cs.AI", "cs.CV"]
```

#### 原因3：时间范围太窄
- ArXiv 每天新增论文有限
- 建议设置合理的 `max_results`

**测试搜索**：
```bash
# 使用宽泛的条件测试
python main.py
# 查看日志中的查询字符串
```

### 5. AI 处理速度慢

**优化建议**：

#### 1. 减少论文数量
```yaml
arxiv:
  max_results: 10  # 从 50 降到 10
```

#### 2. 关闭不需要的功能
```yaml
ai:
  enable_summary: true
  enable_translation: false  # 如果不需要翻译，关闭
  enable_insights: false     # 如果不需要洞察，关闭
```

#### 3. 使用更快的模型
```yaml
openai:
  model: "gpt-3.5-turbo"  # 比 gpt-4 快得多
```

#### 4. 使用本地模型
```yaml
ai:
  provider: "ollama"
  ollama:
    model: "qwen2.5:7b"  # 本地运行，速度快
```

### 6. Docker 部署问题

#### 问题1：容器无法启动
```bash
# 查看详细日志
docker-compose logs -f

# 重新构建镜像
docker-compose build --no-cache

# 删除旧容器重新创建
docker-compose down
docker-compose up -d
```

#### 问题2：无法访问外部网络
```bash
# 检查 Docker 网络
docker network ls

# 使用 host 网络模式（Linux）
docker run --network host ...
```

#### 问题3：配置文件未挂载
```yaml
# docker-compose.yml
volumes:
  - ./config.yaml:/app/config.yaml:ro  # 确保挂载配置文件
  - ./data:/app/data
```

### 7. 权限问题（Linux/Mac）

**症状**：
```
PermissionError: [Errno 13] Permission denied: './data/papers'
```

**解决方案**：
```bash
# 修改目录权限
chmod -R 755 data logs

# 或使用当前用户运行 Docker
docker-compose run --user $(id -u):$(id -g) paper-agent
```

### 8. 中文乱码

**症状**：Markdown 报告或邮件中文显示为乱码

**解决方案**：

1. 确保配置文件使用 UTF-8 编码保存
2. 检查终端编码设置
3. 邮件客户端设置为 UTF-8 显示

**验证方法**：
```bash
# 检查文件编码
file -i config.yaml
# 应显示：charset=utf-8
```

### 9. 获取帮助

如果以上方法都无法解决问题：

1. **查看日志**：
   ```bash
   tail -n 100 logs/arxiv_scraper.log
   ```

2. **启用调试模式**：
   ```yaml
   logging:
     level: "DEBUG"  # 输出详细日志
   ```

3. **提交 Issue**：
   - 提供配置文件（隐去敏感信息）
   - 提供错误日志
   - 说明运行环境（OS、Python版本等）

4. **社区支持**：
   - GitHub Issues: [项目地址]/issues
   - 包含尽可能详细的信息

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
