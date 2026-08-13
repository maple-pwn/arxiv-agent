"""关键词精选：命中标题或摘要的论文被标记 favorites。"""
from __future__ import annotations

import json
import os

from .config import DATA_DIR, load_config


def mark_favorites(config: dict, papers: list[dict]) -> int:
    """就地标记 favorites，返回命中论文篇数。"""
    keywords = config.get("keywords") or []
    if not keywords:
        return 0

    hit_count = 0
    for paper in papers:
        text = (paper.get("title", "") + " " + paper.get("summary", "")).lower()
        hits = []
        for kw in keywords:
            needle = kw.get("keyword", "").lower()
            if needle and needle in text:
                hits.append({"keyword": kw.get("keyword", ""), "reason": kw.get("reason", "")})
        paper["favorites"] = hits
        if hits:
            hit_count += 1
    return hit_count


def run(config: dict, date_str: str) -> None:
    path = os.path.join(DATA_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在：{path}，请先运行 fetch")
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    hit = mark_favorites(config, payload["papers"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"[filter] {date_str}: 命中关键词 {hit} 篇")


if __name__ == "__main__":
    import sys

    cfg = load_config()
    run(cfg, sys.argv[1])
