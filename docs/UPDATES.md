# 功能更新说明

本文档记录了最新的功能更新和改进。

## 最新更新 (2026-01-13)

### 1. 修复Markdown邮件发送问题 ✅

**问题**：SMTP连接超时导致Markdown报告无法发送

**解决方案**：
- 增加邮件发送重试机制（最多3次，每次间隔5秒）
- 添加Webhook方式发送报告（推荐用于Serverless环境）
- 优化错误提示和诊断信息

**相关文件**：
- `src/utils.py` - 新增 `send_email_with_retry()` 和 `send_report_via_webhook()`
- `src/arxiv_scraper.py` - 更新邮件发送逻辑

**使用方法**：
```yaml
# config.yaml
notification:
  enabled: true
  method: webhook  # 或 email
  webhook:
    url: "https://your-webhook-endpoint.com/arxiv"
    method: "POST"
```

### 2. 增强AI Insight生成 ✅

**改进**：
- AI总结现在包含4个维度：核心观点、研究方法、关键结果、应用价值
- 更结构化的输出格式
- 更专业的学术表达

**相关文件**：
- `src/ai_service.py` - 优化summarize_paper方法

**效果对比**：

之前：
```
简单的一段总结文字...
```

现在：
```
### 1. **核心观点**
论文提出了XXX方法，主要创新点在于...

### 2. **研究方法**
使用了YYY技术框架...

### 3. **关键结果**
实验表明...

### 4. **应用价值**
可应用于...
```

### 3. 环境变量支持（Serverless部署准备） ✅

**新增功能**：
- 支持通过环境变量配置所有参数
- 环境变量优先级高于config.yaml
- 完善的默认配置

**相关文件**：
- `src/config_loader.py` - 新增配置加载器
- `.env.example` - 环境变量示例
- `serverless_handler.py` - Serverless函数入口

**支持的环境变量**：
```bash
# ArXiv配置
ARXIV_KEYWORDS=machine learning,deep learning
ARXIV_MAX_RESULTS=10

# AI配置
OPENAI_API_KEY=sk-...
AI_PROVIDER=openai

# 邮件配置
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=your_password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com

# Webhook配置
WEBHOOK_URL=https://your-webhook.com
NOTIFICATION_METHOD=webhook
```

### 4. Serverless部署支持 ✅

**新增文件**：
- `serverless.yml` - Serverless Framework配置
- `serverless_handler.py` - Lambda/函数计算入口
- `docs/SERVERLESS_DEPLOYMENT.md` - 详细部署指南

**支持平台**：
- ✅ AWS Lambda
- ✅ 阿里云函数计算
- ✅ 腾讯云SCF
- ✅ 其他Serverless平台

**特性**：
- 定时触发（Cron表达式）
- 环境变量配置
- 自动依赖打包
- 成本优化（在免费额度内）

**快速部署**：
```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env文件

# 2. 部署
serverless deploy

# 3. 测试
serverless invoke -f arxivScraper
```

### 5. Prompt自定义功能 ✅

**新增功能**：
- 将所有AI Prompt提取到独立配置文件
- 支持自定义prompt模板
- 支持多种prompt类型

**相关文件**：
- `prompts/prompts.yaml` - Prompt配置文件
- `src/prompt_loader.py` - Prompt加载器
- `docs/CUSTOM_PROMPTS.md` - 自定义指南

**内置Prompt类型**：
- `summarize` - 论文总结
- `translate` - 摘要翻译
- `insights` - 关键洞察

**自定义示例**：
```yaml
# prompts/prompts.yaml
custom:
  product_summary:
    system: "你是一位技术产品经理。"
    user_template: |
      从产品角度分析以下论文：
      标题：{title}
      摘要：{summary}

      请说明：
      1. 解决什么问题
      2. 用户价值
      3. 落地难度
      4. 商业潜力
```

### 6. 文档完善 ✅

新增文档：
- `docs/SERVERLESS_DEPLOYMENT.md` - Serverless部署完整指南
- `docs/CUSTOM_PROMPTS.md` - Prompt自定义详细教程
- `docs/UPDATES.md` - 本更新说明文档

## 配置示例

### 完整的config.yaml示例

```yaml
arxiv:
  keywords: ["machine learning", "deep learning"]
  categories: ["cs.AI", "cs.LG"]
  max_results: 10
  sort_by: "submittedDate"
  sort_order: "descending"

storage:
  data_dir: "./data/papers"
  format: "both"
  download_pdf: false
  auto_cleanup: true  # 邮件发送后自动删除

ai:
  enabled: true
  provider: "openai"
  enable_summary: true
  enable_translation: true
  enable_insights: true
  send_markdown_report: true

  openai:
    api_key: "your_api_key"
    model: "gpt-3.5-turbo"
    base_url: "https://api.openai.com/v1"

notification:
  enabled: true
  method: "webhook"  # 推荐用webhook而非email

  webhook:
    url: "https://your-api.com/arxiv"
    method: "POST"

  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your@gmail.com"
    password: "app_password"
    recipients:
      - "recipient@example.com"
```

## 使用场景

### 场景1：本地定时任务

适合有稳定服务器的用户：

```bash
# 1. 配置config.yaml
# 2. 启动定时任务
python main.py --schedule
```

### 场景2：Serverless云端部署

适合希望零运维成本的用户：

```bash
# 1. 配置.env环境变量
# 2. 部署到云端
serverless deploy
```

### 场景3：CI/CD集成

适合集成到开发流程的用户：

```yaml
# .github/workflows/arxiv.yml
name: ArXiv Daily
on:
  schedule:
    - cron: '0 9 * * *'
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run ArXiv Scraper
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          WEBHOOK_URL: ${{ secrets.WEBHOOK_URL }}
        run: python serverless_handler.py
```

## 性能优化

### 1. 邮件发送

- ✅ 增加重试机制（3次）
- ✅ 支持Webhook替代SMTP
- ✅ 超时时间优化（30秒）

### 2. 文件存储

- ✅ 自动清理功能（`auto_cleanup: true`）
- ✅ 仅在邮件成功后删除
- ✅ 失败时保留文件供调试

### 3. Serverless优化

- ✅ 依赖包大小优化
- ✅ 冷启动时间优化
- ✅ 内存和超时配置建议

## 常见问题

### Q1: 邮件一直发送失败怎么办？

A1: 推荐切换到Webhook方式：
```yaml
notification:
  method: webhook
  webhook:
    url: your_webhook_url
```

### Q2: 如何自定义AI生成的内容？

A2: 编辑 `prompts/prompts.yaml` 文件，参考 `docs/CUSTOM_PROMPTS.md`

### Q3: Serverless部署成本如何？

A3: 基本在免费额度内（每月100万次请求）。详见 `docs/SERVERLESS_DEPLOYMENT.md`

### Q4: 如何在现有项目上更新？

A4:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## 下一步计划

未来可能的功能（欢迎贡献）：

- [ ] 支持更多云平台（Google Cloud Functions、Azure Functions）
- [ ] 支持对象存储（S3、OSS）
- [ ] 支持数据库存储（MongoDB、PostgreSQL）
- [ ] Web管理界面
- [ ] 论文推荐系统
- [ ] 多语言报告（英文、日文等）
- [ ] RSS订阅支持
- [ ] 论文相似度分析

## 贡献指南

欢迎提交Issue和Pull Request！

- Issue: 报告Bug或提出功能建议
- PR: 贡献代码或文档改进

## 许可证

本项目采用MIT许可证。
