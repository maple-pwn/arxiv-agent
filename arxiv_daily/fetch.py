"""从 arXiv API 抓取指定日期的论文并落盘到 data/YYYY-MM-DD.json。

日期按「arXiv 发布日」（UTC 口径）分桶，与原站归档口径一致：arXiv 每个工作日
14:00 ET 截止、20:00 ET 发布，此处用 America/New_York 判断截止时间，再取发布
时刻对应的 UTC 日期作为归档日期。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from zoneinfo import ZoneInfo

import feedparser
import httpx

from .config import DATA_DIR, load_config

ARXIV_API = "http://export.arxiv.org/api/query"
PAGE_SIZE = 200
MAX_PAGES = 50  # 安全上限，单日理论不会超过 50*200=10000 篇
SLEEP_SECONDS = 3  # 对 arXiv 礼貌限速


def _arxiv_id_from_url(url: str) -> str | None:
    match = re.search(r"/abs/([^/]+)$", url)
    if not match:
        return None
    return re.sub(r"v\d+$", "", match.group(1))


def _categories(entry) -> list[str]:
    tags = entry.get("tags", []) or []
    return [t.get("term") for t in tags if t.get("term")]


def _primary_category(entry) -> str:
    primary = entry.get("arxiv_primary_category") or entry.get("primary_category")
    if isinstance(primary, dict) and primary.get("term"):
        return primary["term"]
    cats = _categories(entry)
    return cats[0] if cats else ""


def _authors(entry) -> list[str]:
    authors = entry.get("authors") or []
    if not authors and entry.get("author"):
        authors = [entry["author"]]
    return [a.get("name", "") for a in authors if a.get("name")]


def _parse_entry(entry) -> dict | None:
    arxiv_id = _arxiv_id_from_url(entry.get("id", ""))
    if not arxiv_id:
        return None
    return {
        "arxiv_id": arxiv_id,
        "primary_category": _primary_category(entry),
        "categories": _categories(entry),
        "title": re.sub(r"\s+", " ", entry.get("title", "")).strip(),
        "summary": re.sub(r"\s+", " ", entry.get("summary", "")).strip(),
        "authors": _authors(entry),
        "published": entry.get("published", ""),
        "title_zh": None,
        "abstract_zh": None,
        "favorites": [],
    }


def _parse_published(value) -> dt.datetime | None:
    """把 Atom 的 published 字符串解析成带时区的 datetime。"""
    if isinstance(value, dt.datetime):
        return value
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return None


_ANNOUNCE_TZ = ZoneInfo("America/New_York")


def _announcement_date(published) -> dt.date | None:
    """返回论文的 arXiv 发布日（UTC 口径），与原站归档日期对齐。

    arXiv 每个工作日 14:00 ET 截止、20:00 ET 发布。用 America/New_York 判断
    是否已过当日截止（14:00），再取 20:00 ET 发布时刻对应的 UTC 日期。
    周末少量边界论文可能有 ±1 天偏差，可接受。
    """
    parsed = _parse_published(published)
    if parsed is None:
        return None
    eastern = parsed.astimezone(_ANNOUNCE_TZ)
    if eastern.hour >= 14:
        eastern += dt.timedelta(days=1)
    announce_et = eastern.replace(hour=20, minute=0, second=0, microsecond=0)
    return announce_et.astimezone(dt.timezone.utc).date()


def _build_query(categories: dict) -> str:
    return "(" + " OR ".join(f"cat:{code}" for code in categories) + ")"


def fetch_date(config: dict, date_str: str) -> list[dict]:
    """抓取某一天的全部论文，返回解析后的论文列表（按 category/id 排序）。"""
    target = dt.date.fromisoformat(date_str)
    query = _build_query(config["categories"])
    papers: dict[str, dict] = {}

    with httpx.Client(follow_redirects=True, timeout=60) as client:
        for page in range(MAX_PAGES):
            params = {
                "search_query": query,
                "start": page * PAGE_SIZE,
                "max_results": PAGE_SIZE,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            resp = client.get(ARXIV_API, params=params)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            entries = feed.entries
            if not entries:
                break

            stop = False
            for entry in entries:
                paper = _parse_entry(entry)
                if not paper:
                    continue
                pdate = _announcement_date(paper["published"])
                if pdate is None:
                    # 日期无法解析的兜底收录
                    papers[paper["arxiv_id"]] = paper
                    continue
                if pdate > target:
                    continue  # 比目标日期新（理论上不会出现），跳过
                if pdate < target:
                    stop = True  # 已越过目标日期，无需继续翻页
                    break
                papers[paper["arxiv_id"]] = paper

            if stop or len(entries) < PAGE_SIZE:
                break
            time.sleep(SLEEP_SECONDS)

    result = sorted(
        papers.values(),
        key=lambda p: (p["primary_category"], p["arxiv_id"]),
    )
    print(f"[fetch] {date_str}: 抓取到 {len(result)} 篇论文")
    return result


def _load_existing(date_str: str) -> dict | None:
    path = os.path.join(DATA_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_merge(date_str: str, new_papers: list[dict]) -> int:
    """合并写回 data 文件：保留已有论文的翻译/精选字段。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    existing = _load_existing(date_str)
    old_by_id: dict[str, dict] = {}
    if existing:
        old_by_id = {p["arxiv_id"]: p for p in existing.get("papers", [])}

    merged: dict[str, dict] = {}
    for paper in new_papers:
        aid = paper["arxiv_id"]
        if aid in old_by_id:
            old = old_by_id[aid]
            paper["title_zh"] = old.get("title_zh")
            paper["abstract_zh"] = old.get("abstract_zh")
            paper["favorites"] = old.get("favorites", [])
        merged[aid] = paper

    papers = sorted(
        merged.values(),
        key=lambda p: (p["primary_category"], p["arxiv_id"]),
    )
    payload = {"date": date_str, "papers": papers}
    path = os.path.join(DATA_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return len(papers)


def run(config: dict, date_str: str) -> None:
    papers = fetch_date(config, date_str)
    if papers:
        save_merge(date_str, papers)


if __name__ == "__main__":
    import sys

    cfg = load_config()
    run(cfg, sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat())
