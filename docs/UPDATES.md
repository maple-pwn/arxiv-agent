# 功能更新说明

本文档记录了最新的功能更新和改进。

## 最新更新 (2026-01-13)

### 1. 修复Markdown邮件发送问题 ✅

**问题**：SMTP连接超时导致Markdown报告无法发送

**解决方案**：
- 增加邮件发送重试机制（最多3次，每次间隔5秒）
- 添加Webhook方式发送报告
- 优化错误提示和诊断信息

**相关文件**：
- `src/utils.py` - 新增 `send_email_with_retry()` 和 `send_report_via_webhook()`
- `src/arxiv_scraper.py` - 更新邮件发送逻辑

**使用方法**：

邮件方式（带重试）：
```yaml
# config.yaml
notification:
  enabled: true
  method: email
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your@gmail.com"
    password: "your_app_password"
    recipients:
      - "recipient@example.com"
```

Webhook方式（推荐）：
```yaml
notification:
  enabled: true
  method: webhook
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

### 3. Prompt自定义功能 ✅

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

### 4. AI智能筛选功能 ✅

**新增功能**：在AI处理前，通过AI判断论文与用户关键词的相关性，过滤不相关论文。

**功能特点**：
- 基于用户自定义关键词进行相关性判断
- 可配置置信度阈值（0.0-1.0）
- 节省AI处理成本（只处理相关论文）
- 提升报告质量（过滤无关内容）
- 保守策略：出错时默认保留论文

**相关文件**：
- `prompts/prompts.yaml` - 新增 `filter` prompt模板
- `src/ai_service.py` - 新增 `filter_paper()` 方法
- `src/arxiv_scraper.py` - 新增 `filter_papers_with_ai()` 方法
- `config.yaml.template` - 新增筛选配置项

**配置示例**：

```yaml
ai:
  # 启用AI智能筛选
  enable_filter: true

  # 筛选关键词（用逗号分隔）
  filter_keywords: "强化学习应用, 游戏AI, 多智能体系统"

  # 置信度阈值（0.6-0.8推荐）
  filter_threshold: 0.7
```

**工作流程**：
1. ArXiv搜索论文 → 获得50篇
2. AI智能筛选 → 保留15篇相关论文
3. AI深度处理 → 总结、翻译、提取洞察
4. 生成报告 → 只包含15篇高相关性论文

**使用场景**：
- ArXiv搜索关键词太宽泛，返回很多不相关论文
- 希望聚焦特定研究方向或应用场景
- 需要降低AI处理成本（只处理相关论文）

**效果对比**：

```
# 未启用筛选
搜索到50篇论文 → AI处理50篇 → 成本：$0.10

# 启用筛选（阈值0.7）
搜索到50篇论文 → AI筛选50篇 → 保留15篇 → AI处理15篇 → 成本：$0.05
节省成本：50% + 报告质量提升
```

### 5. 文档完善 ✅

新增文档：
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

### 场景2：CI/CD集成

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
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run ArXiv Scraper
        run: python main.py
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

### 3. AI处理

- ✅ 结构化prompt提升质量
- ✅ 可自定义prompt模板
- ✅ 支持多种AI服务商

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

### Q3: 如何在现有项目上更新？

A3:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## 下一步计划

未来可能的功能（欢迎贡献）：

- [ ] 支持更多AI提供商（Google Gemini、Cohere等）
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