# arXiv 每日论文阅读站

一个每日自动抓取 arXiv 论文、用 LLM 翻译成中文、生成静态网页的「论文每日摘要」站。
数据以 JSON 提交进仓库，站点为纯静态页面，托管在 GitHub Pages 上，由 GitHub Actions 定时更新。

> 复刻自 `https://paper.axi404.top/` 的形态：分类侧边栏、英文+中文标题摘要、
> 客户端「收藏清单」、关键词精选、以及每篇的「AI Translation」跳转按钮（指向
> [幻觉翻译 hjfy.top](https://hjfy.top)）。

## 功能

- **每日抓取**：调 arXiv 官方 API，按分类抓取某天的全部论文（支持回溯补数据）。
- **LLM 翻译**：标题 + 摘要自动翻译成简体中文（OpenAI 兼容接口，默认 DeepSeek，可配）。
- **关键词精选**：命中配置关键词的论文自动置顶高亮，并标注命中词与理由。
- **客户端收藏清单**：浏览器 localStorage 收藏 arXiv ID，支持「复制全部 ID / 清空」。
- **静态站点**：首页（总量/天数/存储 + 日期归档）+ 每日页（分类侧边栏 + 论文卡片）。
- **可选访问统计**：可注入 Cloudflare Web Analytics / GoatCounter 脚本。

## 快速开始（本地）

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml   # 按需修改分类、关键词、LLM 配置

# 1. 抓取某天论文（默认今天 UTC）
python -m arxiv_daily.cli fetch --date 2026-08-13

# 2. 翻译（需设置 API key；可 --limit 5 先试跑几篇）
DEEPSEEK_API_KEY=sk-xxx python -m arxiv_daily.cli translate --date 2026-08-13 --limit 5

# 3. 关键词精选标记
python -m arxiv_daily.cli filter --date 2026-08-13

# 4. 生成静态站到 docs/
python -m arxiv_daily.cli build

# 预览
python3 -m http.server -d docs 8000
# 打开 http://localhost:8000/
```

一步到位（抓取+翻译+精选+构建）：

```bash
DEEPSEEK_API_KEY=sk-xxx python -m arxiv_daily.cli run --date 2026-08-13
```

> 未设置 API key 时，`translate` 会打印提示并跳过，仍能生成纯英文站点。

## 配置说明（config.yaml）

| 字段 | 说明 |
|---|---|
| `categories` | 抓取的 arXiv 分类 → 中文名映射（侧边栏 / 分组标题） |
| `keywords` | 关键词精选列表，每条含 `keyword` 与 `reason` |
| `llm.base_url` / `model` | 任意 OpenAI 兼容接口；DeepSeek 默认 `https://api.deepseek.com` + `deepseek-chat` |
| `llm.api_key_env` | 从哪个环境变量读 API key（默认 `DEEPSEEK_API_KEY`） |
| `site.base_url` | 部署在 GitHub Pages 子路径时填 `/仓库名`，根域名留空 |
| `analytics` | 可选，分析脚本标签；留空则隐藏访问统计 |

## 部署到 GitHub Pages

1. 把本项目 push 到 GitHub 仓库。
2. 在仓库 **Settings → Secrets and variables → Actions** 里新增 secret：
   `DEEPSEEK_API_KEY`（或你配置的 `llm.api_key_env` 对应的名字）。
3. 在 **Settings → Pages** 里把 **Source** 选为 `Deploy from a branch`，分支 `main`，目录 `/docs`。
4. `.github/workflows/daily.yml` 会每天 UTC 02:30 自动抓取、翻译、构建并提交；
   也可在 **Actions** 页手动 `Run workflow`。

- 若仓库名是 `user.github.io`，`site.base_url` 留空即可；
  否则填 `/仓库名`（例如 `site.base_url: /arxiv-daily`）。

## 数据与目录结构

```
arxiv_daily/            # Python 包：config/fetch/translate/filter/build/cli
  templates/            # Jinja2 模板（index.html / daily.html）
  static/               # style.css / app.js
data/                   # 每日 JSON（原始 + 翻译 + 精选标记），提交进 git
docs/                   # 生成的静态站（GitHub Pages 源），提交进 git
config.yaml             # 用户配置
.github/workflows/daily.yml
```

每天一个 `data/YYYY-MM-DD.json`，结构：

```json
{
  "date": "2026-08-13",
  "papers": [
    {
      "arxiv_id": "2608.11363",
      "primary_category": "cs.RO",
      "categories": ["cs.RO", "cs.AI"],
      "title": "…",
      "summary": "…",
      "authors": ["…"],
      "published": "2026-08-13T…",
      "title_zh": "…",
      "abstract_zh": "…",
      "favorites": [{"keyword": "diffusion", "reason": "扩散模型相关"}]
    }
  ]
}
```

翻译是幂等的：`translate` 只处理缺失 `title_zh` 的论文，可安全重跑、断点续传。

## 说明与常见问题

- **「AI Translation」按钮**：指向 `https://hjfy.top/arxiv/<id>`（幻觉翻译），
  是纯链接跳转，无需 API。它不负责本页面的中文翻译——页面中文来自你配置的 LLM。
- **访问统计**：静态站自身无法计数，需第三方。在 `config.yaml` 的 `analytics` 填入
  [Cloudflare Web Analytics](https://www.cloudflare.com/web-analytics/) 或
  [GoatCounter](https://www.goatcounter.com/) 的 `<script>` 标签即可（免费）。
- **归档日期**：按 arXiv **发布日**（UTC 口径）分桶——arXiv 每个工作日 14:00 ET 截止、
  20:00 ET 发布，代码用 America/New_York 判断截止时间后取发布时刻的 UTC 日期，与原站一致；
  周末少量边界论文可能有 ±1 天偏差。`site.timezone` 仅用于「今天」默认值。
- **定时任务**：UTC 02:30（≈ 北京时间 10:30），此时当日 arXiv 已发布完毕。
- **成本**：默认 DeepSeek，翻译一篇（标题+摘要）约数千 token，单日数百篇成本很低；
  可改用任意 OpenAI 兼容服务或调低 `model`。

## License

MIT
