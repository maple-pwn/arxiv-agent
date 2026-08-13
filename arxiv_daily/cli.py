"""命令行入口：python -m arxiv_daily.cli <fetch|translate|filter|build|run>"""
from __future__ import annotations

import argparse
import datetime as dt
from zoneinfo import ZoneInfo

from . import build, fetch, filter as filter_mod, translate
from .config import load_config


def _today(config: dict) -> str:
    tz = ZoneInfo(config.get("site", {}).get("timezone", "Asia/Shanghai"))
    return dt.datetime.now(tz).date().isoformat()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="arxiv-daily", description="arXiv 每日论文阅读站")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="抓取某天论文")
    p_fetch.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天（按配置时区）")
    p_fetch.add_argument("--config", default="config.yaml")

    p_translate = sub.add_parser("translate", help="LLM 翻译某天论文")
    p_translate.add_argument("--date", default=None)
    p_translate.add_argument("--limit", type=int, default=None, help="只翻译前 N 篇（试跑用）")
    p_translate.add_argument("--config", default="config.yaml")

    p_filter = sub.add_parser("filter", help="关键词精选标记")
    p_filter.add_argument("--date", default=None)
    p_filter.add_argument("--config", default="config.yaml")

    p_build = sub.add_parser("build", help="生成静态站")
    p_build.add_argument("--config", default="config.yaml")

    p_run = sub.add_parser("run", help="一键：fetch + translate + filter + build")
    p_run.add_argument("--date", default=None)
    p_run.add_argument("--limit", type=int, default=None)
    p_run.add_argument("--config", default="config.yaml")

    args = parser.parse_args(argv)
    config = load_config(args.config)
    if getattr(args, "date", None) is None:
        args.date = _today(config)

    if args.command == "fetch":
        fetch.run(config, args.date)
    elif args.command == "translate":
        translate.run(config, args.date, args.limit)
    elif args.command == "filter":
        filter_mod.run(config, args.date)
    elif args.command == "build":
        build.run(config)
    elif args.command == "run":
        fetch.run(config, args.date)
        translate.run(config, args.date, args.limit)
        filter_mod.run(config, args.date)
        build.run(config)


if __name__ == "__main__":
    main()
