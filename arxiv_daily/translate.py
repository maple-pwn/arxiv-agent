"""用 LLM（OpenAI 兼容接口）批量翻译标题与摘要，幂等、可断点续传。"""
from __future__ import annotations

import json
import os
import re
import time

import httpx

from .config import DATA_DIR, get_api_key, load_config

SYSTEM_PROMPT = (
    "你是专业的学术论文翻译，精通中英文学术表达。请将用户给出的英文标题与摘要"
    "完整地逐句翻译成简体中文，忠实于原文：不要总结、不要概括、不要省略任何句子或技术细节，"
    "保持学术术语准确，译文长度应与原文相当。"
    "原文中的 LaTeX 数学公式（形如 $...$ 或 $$...$$）必须原样保留，"
    "不要翻译、不要改写、不要转成普通文字或 Unicode 字符，只翻译公式以外的正文。"
    "严格只输出一个 JSON 对象，格式为 "
    '{"title_zh": "标题中文", "abstract_zh": "摘要中文"}，不要输出任何其他文字。'
)


class AuthError(Exception):
    """API key 无效（401/403）时抛出，用于立即终止而非逐篇重试。"""


def _chat_endpoint(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url + "/chat/completions"


def _extract_json(text: str) -> dict:
    """从 LLM 输出中稳健地解析 JSON 对象。"""
    text = text.strip()
    # 去掉 ```json ... ``` 围栏
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # 兜底：截取第一个 { 到最后一个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def translate_paper(client: httpx.Client, config: dict, key: str, paper: dict) -> tuple[str, str]:
    """翻译单篇，返回 (title_zh, abstract_zh)。"""
    llm = config["llm"]
    endpoint = _chat_endpoint(llm["base_url"])
    user = (
        "请将下面的英文标题和摘要完整翻译成简体中文（逐句翻译、不要总结、不要省略任何内容，"
        "并保留其中的 LaTeX 数学公式 $...$ 原样不动）：\n\n"
        "标题：\n" + paper["title"] + "\n\n摘要：\n" + paper["summary"]
    )
    payload = {
        "model": llm["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    resp = client.post(endpoint, json=payload, headers=headers, timeout=llm.get("timeout", 120))
    if resp.status_code in (401, 403):
        raise AuthError(f"API 认证失败（HTTP {resp.status_code}），请检查 API key 是否有效")
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _extract_json(content)
    title_zh = str(parsed.get("title_zh", "")).strip()
    abstract_zh = str(parsed.get("abstract_zh", "")).strip()
    if not title_zh:
        raise ValueError("LLM 返回的 title_zh 为空")
    return title_zh, abstract_zh


def _load_papers(date_str: str) -> tuple[list[dict], str]:
    path = os.path.join(DATA_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在：{path}，请先运行 fetch")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["papers"], path


def _save_papers(path: str, papers: list[dict]) -> None:
    date_str = os.path.basename(path).removesuffix(".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"date": date_str, "papers": papers}, fh, ensure_ascii=False, indent=2)


def translate_date(config: dict, date_str: str, limit: int | None = None) -> int:
    """翻译某天所有尚未翻译的论文，返回本次翻译的篇数。"""
    key = get_api_key(config)
    if not key:
        print(
            f"[translate] 未设置 API key（环境变量 "
            f"{config['llm'].get('api_key_env', 'DEEPSEEK_API_KEY')}），跳过翻译"
        )
        return 0

    papers, path = _load_papers(date_str)
    pending = [p for p in papers if not p.get("title_zh")]
    if limit is not None:
        pending = pending[:limit]

    if not pending:
        print(f"[translate] {date_str}: 无待翻译论文（已全部翻译）")
        return 0

    llm = config["llm"]
    max_retries = int(llm.get("max_retries", 3))
    done = 0
    with httpx.Client(follow_redirects=True) as client:
        for i, paper in enumerate(pending, 1):
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    title_zh, abstract_zh = translate_paper(client, config, key, paper)
                    paper["title_zh"] = title_zh
                    paper["abstract_zh"] = abstract_zh
                    done += 1
                    print(f"[translate] {date_str}: {i}/{len(pending)} {paper['arxiv_id']} 完成")
                    break
                except AuthError as err:
                    print(f"[translate] {err}，终止翻译")
                    _save_papers(path, papers)
                    return done
                except (httpx.HTTPError, ValueError, KeyError, IndexError, json.JSONDecodeError) as err:
                    last_err = err
                    wait = 2 ** attempt
                    print(f"[translate] {paper['arxiv_id']} 第 {attempt + 1} 次失败：{err}，{wait}s 后重试")
                    time.sleep(wait)
            else:
                print(f"[translate] {paper['arxiv_id']} 重试耗尽，跳过：{last_err}")
            time.sleep(0.5)  # 温和限速

            # 每 10 篇保存一次，断点续传
            if i % 10 == 0:
                _save_papers(path, papers)

    _save_papers(path, papers)
    print(f"[translate] {date_str}: 本次翻译 {done} 篇")
    return done


def run(config: dict, date_str: str, limit: int | None = None) -> None:
    translate_date(config, date_str, limit)


if __name__ == "__main__":
    import sys

    cfg = load_config()
    translate_date(cfg, sys.argv[1])
