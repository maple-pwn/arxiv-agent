#!/usr/bin/env python3
"""
ArXiv 论文自动抓取工具
主入口文件
"""

import os
import sys
import argparse
import logging
import schedule
import time
from datetime import datetime

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import ConfigManager
from src.config_loader import load_config
from src.arxiv_scraper import ArxivScraper
from src.utils import setup_logging, send_notification, format_paper_summary, ensure_directories


def run_scraper(config_manager: ConfigManager) -> None:
    """
    执行一次论文抓取任务

    Args:
        config_manager: 配置管理器
    """
    logger = logging.getLogger(__name__)

    try:
        # 创建抓取器实例
        scraper = ArxivScraper(config_manager.config)

        # 执行抓取
        result = scraper.run()

        # 发送通知
        if result['success']:
            notification_config = config_manager.get('notification', {})
            if notification_config.get('enabled', False):
                papers = []  # 这里可以改进，保存抓取结果供通知使用
                message = f"成功抓取 {result['paper_count']} 篇论文\n"
                message += f"执行时间: {result['timestamp']}"
                send_notification(notification_config, message, "ArXiv 论文抓取成功")

    except Exception as e:
        logger.error(f"执行抓取任务时出错: {str(e)}", exc_info=True)

        # 发送错误通知
        notification_config = config_manager.get('notification', {})
        if notification_config.get('enabled', False):
            message = f"抓取任务执行失败\n错误信息: {str(e)}"
            send_notification(notification_config, message, "ArXiv 论文抓取失败")


def run_once(config_path: str) -> None:
    """
    执行一次抓取任务

    Args:
        config_path: 配置文件路径
    """
    # 加载配置
    config_manager = ConfigManager(config_path)

    # 设置日志
    logging_config = config_manager.get('logging', {})
    setup_logging(logging_config)

    # 确保目录存在
    ensure_directories(config_manager.config)

    logger = logging.getLogger(__name__)
    logger.info("以单次模式运行")

    # 执行抓取
    run_scraper(config_manager)


def run_scheduled(config_path: str) -> None:
    """
    以调度模式运行

    Args:
        config_path: 配置文件路径
    """
    # 加载配置
    config_manager = ConfigManager(config_path)

    # 设置日志
    logging_config = config_manager.get('logging', {})
    setup_logging(logging_config)

    # 确保目录存在
    ensure_directories(config_manager.config)

    logger = logging.getLogger(__name__)

    # 获取调度配置
    schedule_config = config_manager.get('schedule', {})

    if not schedule_config.get('enabled', False):
        logger.warning("调度功能未启用，使用单次模式")
        run_scraper(config_manager)
        return

    # 设置定时任务
    schedule_time = schedule_config.get('time', '09:00')
    schedule.every().day.at(schedule_time).do(run_scraper, config_manager)

    logger.info(f"调度模式已启动，将在每天 {schedule_time} 执行抓取任务")
    logger.info("按 Ctrl+C 停止")

    # 立即执行一次（可选）
    if schedule_config.get('run_on_start', False):
        logger.info("执行启动时抓取")
        run_scraper(config_manager)

    # 循环等待
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在退出...")


def create_sample_config() -> None:
    """创建示例配置文件"""
    if os.path.exists('config.yaml'):
        print("配置文件 config.yaml 已存在")
        response = input("是否覆盖? (y/N): ")
        if response.lower() != 'y':
            print("取消创建")
            return

    try:
        # 复制模板文件
        if os.path.exists('config.yaml.template'):
            import shutil
            shutil.copy('config.yaml.template', 'config.yaml')
            print("已从模板创建配置文件: config.yaml")
        else:
            # 创建简单的配置文件
            import yaml
            default_config = {
                'arxiv': {
                    'keywords': ['machine learning'],
                    'categories': ['cs.AI', 'cs.LG'],
                    'max_results': 50,
                    'sort_by': 'submittedDate',
                    'sort_order': 'descending'
                },
                'schedule': {
                    'enabled': True,
                    'time': '09:00'
                },
                'storage': {
                    'data_dir': './data/papers',
                    'format': 'both',
                    'download_pdf': False
                },
                'logging': {
                    'level': 'INFO',
                    'file': './logs/arxiv_scraper.log',
                    'console': True
                }
            }

            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

            print("已创建默认配置文件: config.yaml")

        print("\n请根据需要修改配置文件后再运行")

    except Exception as e:
        print(f"创建配置文件失败: {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ArXiv 论文自动抓取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 使用默认配置运行一次
  %(prog)s --schedule         # 以调度模式运行
  %(prog)s --config my.yaml   # 使用指定配置文件
  %(prog)s --init             # 创建示例配置文件
        """
    )

    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )

    parser.add_argument(
        '-s', '--schedule',
        action='store_true',
        help='以调度模式运行（定时执行）'
    )

    parser.add_argument(
        '--init',
        action='store_true',
        help='创建示例配置文件'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='ArXiv Scraper 1.0.0'
    )

    args = parser.parse_args()

    # 创建示例配置
    if args.init:
        create_sample_config()
        return

    # 检查配置文件
    if not os.path.exists(args.config):
        print(f"错误: 配置文件不存在: {args.config}")
        print(f"请运行 '{sys.argv[0]} --init' 创建示例配置文件")
        sys.exit(1)

    # 运行
    try:
        if args.schedule:
            run_scheduled(args.config)
        else:
            run_once(args.config)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
