# Serverless部署指南

本指南介绍如何将ArXiv论文抓取工具部署到Serverless平台（AWS Lambda、阿里云函数计算、腾讯云SCF等）。

## 目录

- [准备工作](#准备工作)
- [配置环境变量](#配置环境变量)
- [AWS Lambda部署](#aws-lambda部署)
- [阿里云函数计算部署](#阿里云函数计算部署)
- [本地测试](#本地测试)
- [注意事项](#注意事项)

## 准备工作

### 1. 安装Serverless Framework

```bash
npm install -g serverless
```

### 2. 安装Python依赖插件

```bash
npm install --save-dev serverless-python-requirements
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写实际配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写以下必需配置：

```bash
# AI配置（必需）
OPENAI_API_KEY=your_openai_api_key_here

# 邮件配置（必需，如果使用邮件通知）
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient@example.com

# 或者使用Webhook（可选）
# NOTIFICATION_METHOD=webhook
# WEBHOOK_URL=https://your-webhook-endpoint.com/arxiv
```

## AWS Lambda部署

### 1. 配置AWS凭证

```bash
serverless config credentials --provider aws --key YOUR_ACCESS_KEY --secret YOUR_SECRET_KEY
```

### 2. 修改serverless.yml

编辑 `serverless.yml` 中的配置：

```yaml
provider:
  name: aws
  runtime: python3.9
  region: us-east-1  # 根据需要修改
```

### 3. 部署

```bash
serverless deploy
```

### 4. 手动触发测试

```bash
serverless invoke -f arxivScraper
```

### 5. 查看日志

```bash
serverless logs -f arxivScraper -t
```

## 阿里云函数计算部署

### 1. 安装阿里云插件

```bash
npm install --save-dev serverless-aliyun-function-compute
```

### 2. 修改serverless.yml

```yaml
provider:
  name: aliyun
  runtime: python3.9
  credentials: ~/.aliyuncli/credentials
```

### 3. 配置阿里云凭证

在 `~/.aliyuncli/credentials` 中配置：

```ini
[default]
aliyun_access_key_id = YOUR_ACCESS_KEY_ID
aliyun_access_key_secret = YOUR_ACCESS_KEY_SECRET
```

### 4. 部署

```bash
serverless deploy
```

## 本地测试

### 使用serverless-offline插件

```bash
npm install --save-dev serverless-offline
serverless offline start
```

### 直接运行handler

```bash
python serverless_handler.py
```

## 环境变量配置详解

### 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-...` |
| `EMAIL_SENDER` | 发件人邮箱 | `your@gmail.com` |
| `EMAIL_PASSWORD` | 邮箱密码/应用专用密码 | `xxxx xxxx xxxx xxxx` |
| `EMAIL_RECIPIENTS` | 收件人（逗号分隔） | `user1@example.com,user2@example.com` |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ARXIV_MAX_RESULTS` | 每次抓取论文数量 | `10` |
| `ARXIV_KEYWORDS` | 关键词（逗号分隔） | `machine learning,deep learning` |
| `NOTIFICATION_METHOD` | 通知方式 | `email` |
| `STORAGE_AUTO_CLEANUP` | 自动清理本地文件 | `true` |

## 使用Webhook替代邮件

对于Serverless环境，推荐使用Webhook方式发送报告，避免SMTP连接问题：

```bash
NOTIFICATION_METHOD=webhook
WEBHOOK_URL=https://your-api-gateway.com/arxiv-report
WEBHOOK_METHOD=POST
```

Webhook接收的JSON格式：

```json
{
  "type": "arxiv_report",
  "timestamp": "20260113_120000",
  "paper_count": 5,
  "content": "# ArXiv 论文日报\\n\\n...",
  "format": "markdown"
}
```

## 定时任务配置

在 `serverless.yml` 中配置定时触发：

```yaml
functions:
  arxivScraper:
    handler: serverless_handler.lambda_handler
    events:
      # 每天UTC时间9:00执行
      - schedule:
          rate: cron(0 9 * * ? *)
          enabled: true

      # 或者使用rate表达式
      # - schedule:
      #     rate: rate(1 day)
```

### Cron表达式示例

- `cron(0 9 * * ? *)` - 每天9:00 UTC
- `cron(0 0/12 * * ? *)` - 每12小时
- `cron(0 18 ? * MON-FRI *)` - 工作日18:00

## 注意事项

### 1. 超时设置

论文抓取和AI处理可能需要较长时间，建议设置至少5分钟超时：

```yaml
provider:
  timeout: 300  # 5分钟
```

### 2. 内存配置

AI处理需要较多内存，建议至少512MB：

```yaml
provider:
  memorySize: 512
```

### 3. 依赖包大小

如果部署包过大，可以：

- 启用 `dockerizePip: true` 使用Docker构建
- 启用 `slim: true` 删除不必要的文件
- 考虑使用Lambda Layers

### 4. 文件存储

Serverless环境的`/tmp`目录有限（512MB），建议：

- 启用 `auto_cleanup: true` 自动删除文件
- 不下载PDF：`download_pdf: false`
- 使用Webhook而非邮件附件

### 5. 冷启动

首次调用可能需要10-30秒冷启动时间，这是正常现象。可以通过以下方式优化：

- 使用预留并发
- 优化依赖包大小
- 使用Lambda SnapStart（Java运行时）

## 成本估算

### AWS Lambda

- 免费额度：每月100万次请求 + 40万GB-秒
- 每天执行1次，每次300秒，512MB内存
- 月成本：约 $0（在免费额度内）

### 阿里云函数计算

- 免费额度：每月100万次调用 + 40万CU-秒
- 成本类似AWS，基本在免费额度内

## 故障排查

### 1. 超时错误

增加超时时间或减少 `max_results`：

```bash
ARXIV_MAX_RESULTS=5
```

### 2. 内存不足

增加内存配置：

```yaml
provider:
  memorySize: 1024
```

### 3. 邮件发送失败

切换到Webhook方式：

```bash
NOTIFICATION_METHOD=webhook
WEBHOOK_URL=your_webhook_url
```

### 4. API密钥错误

检查环境变量是否正确设置：

```bash
serverless invoke -f arxivScraper --log
```

## 监控和日志

### CloudWatch日志（AWS）

```bash
# 实时查看日志
serverless logs -f arxivScraper -t

# 查看最近日志
serverless logs -f arxivScraper --startTime 5m
```

### 配置告警

在 `serverless.yml` 中添加CloudWatch告警：

```yaml
resources:
  Resources:
    ErrorAlarm:
      Type: AWS::CloudWatch::Alarm
      Properties:
        AlarmName: ArxivScraperErrors
        MetricName: Errors
        Namespace: AWS/Lambda
        Statistic: Sum
        Period: 300
        EvaluationPeriods: 1
        Threshold: 1
        ComparisonOperator: GreaterThanThreshold
```

## 更新部署

```bash
# 更新代码
serverless deploy

# 仅更新函数代码（更快）
serverless deploy function -f arxivScraper
```

## 删除部署

```bash
serverless remove
```

## 相关链接

- [Serverless Framework文档](https://www.serverless.com/framework/docs)
- [AWS Lambda文档](https://docs.aws.amazon.com/lambda/)
- [阿里云函数计算文档](https://help.aliyun.com/product/50980.html)
