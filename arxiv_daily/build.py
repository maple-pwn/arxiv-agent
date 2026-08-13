"""读取 data/ 下的 JSON，用 Jinja2 渲染静态站到 docs/。"""
from __future__ import annotations

import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import DATA_DIR, DOCS_DIR, category_name, load_config

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")
STATIC_DIR = os.path.join(HERE, "static")


def _load_all_dates() -> dict[str, dict]:
    """返回 {date_str: payload}，按日期倒序。"""
    if not os.path.isdir(DATA_DIR):
        return {}
    dates: dict[str, dict] = {}
    for name in sorted(os.listdir(DATA_DIR), reverse=True):
        if not name.endswith(".json") or name == "index.json":
            continue
        date_str = name.removesuffix(".json")
        with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as fh:
            dates[date_str] = json.load(fh)
    return dates


def _storage_mb() -> float:
    total = 0
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            if name.endswith(".json"):
                total += os.path.getsize(os.path.join(DATA_DIR, name))
    return round(total / (1024 * 1024), 2)


def _display_category(config: dict, paper: dict) -> str:
    """每篇论文的展示分类：主分类在配置内则用主分类，否则回退到首个交叉列表的配置分类。"""
    configured = set(config["categories"].keys())
    primary = paper.get("primary_category", "")
    if primary in configured:
        return primary
    for code in paper.get("categories", []):
        if code in configured:
            return code
    return primary or "cs"


def _group_by_category(config: dict, papers: list[dict]) -> list[dict]:
    """按展示分类分组，返回有序分组（配置内顺序优先）。"""
    order = list(config["categories"].keys())
    grouped: dict[str, list[dict]] = {}
    for paper in papers:
        paper["group"] = _display_category(config, paper)
        grouped.setdefault(paper["group"], []).append(paper)

    codes = [c for c in order if c in grouped]
    codes += sorted(set(grouped) - set(order))

    return [
        {
            "code": code,
            "name_zh": category_name(config, code),
            "count": len(grouped[code]),
            "papers": grouped[code],
        }
        for code in codes
    ]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )


def build_index(config: dict, env: Environment, dates: dict[str, dict]) -> None:
    total_papers = sum(len(p["papers"]) for p in dates.values())
    stats = {
        "total": total_papers,
        "days": len(dates),
        "storage_mb": _storage_mb(),
    }
    template = env.get_template("index.html")
    html = template.render(
        base_url=config["site"].get("base_url", ""),
        site=config["site"],
        analytics=config.get("analytics", ""),
        stats=stats,
        dates=list(dates.keys()),
    )
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[build] 首页已生成（{stats['total']} 篇 / {stats['days']} 天 / {stats['storage_mb']} MB）")


def build_daily(config: dict, env: Environment, date_str: str, papers: list[dict]) -> None:
    # 先标注展示分类（主分类不在配置内时回退到交叉列表的配置分类）
    for paper in papers:
        paper["group"] = _display_category(config, paper)

    favorites = [p for p in papers if p.get("favorites")]
    fav_ids = {p["arxiv_id"] for p in favorites}
    # 精选论文置顶单独展示，普通分类中剔除，避免重复
    categories = _group_by_category(config, [p for p in papers if p["arxiv_id"] not in fav_ids])
    translated = sum(1 for p in papers if p.get("title_zh"))
    stats = {"papers": len(papers), "categories": len(categories), "translated": translated}

    template = env.get_template("daily.html")
    html = template.render(
        base_url=config["site"].get("base_url", ""),
        site=config["site"],
        analytics=config.get("analytics", ""),
        date=date_str,
        stats=stats,
        categories=categories,
        favorites=favorites,
    )
    out_dir = os.path.join(DOCS_DIR, "daily")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{date_str}.html"), "w", encoding="utf-8") as fh:
        fh.write(html)


def _copy_static() -> None:
    dest = os.path.join(DOCS_DIR, "static")
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(STATIC_DIR):
        src = os.path.join(STATIC_DIR, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, name))


def build(config: dict) -> None:
    env = _env()
    dates = _load_all_dates()
    build_index(config, env, dates)
    for date_str, payload in dates.items():
        build_daily(config, env, date_str, payload["papers"])
    _copy_static()
    print(f"[build] 完成，共生成 {len(dates)} 个日期页")


def run(config: dict) -> None:
    build(config)


if __name__ == "__main__":
    cfg = load_config()
    run(cfg)
