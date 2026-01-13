"""
Serverless 函数入口
用于AWS Lambda、阿里云函数计算等Serverless平台
"""

import os
import sys
import json
import logging

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_loader import load_config
from src.arxiv_scraper import ArxivScraper
from src.utils import setup_logging, ensure_directories


def handler(event, context):
    """
    Serverless函数处理器

    Args:
        event: 触发事件
        context: 运行上下文

    Returns:
        响应结果
    """
    try:
        # 加载配置（支持环境变量）
        config = load_config()

        # 设置日志（Serverless环境通常使用stdout）
        logging_config = config.get('logging', {})
        logging_config['console'] = True  # 强制输出到控制台
        setup_logging(logging_config)

        logger = logging.getLogger(__name__)
        logger.info("Serverless函数开始执行")

        # 创建抓取器实例
        scraper = ArxivScraper(config)

        # 执行抓取任务
        result = scraper.run()

        # 返回结果
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'success': result.get('success', False),
                'paper_count': result.get('paper_count', 0),
                'timestamp': result.get('timestamp'),
                'message': '论文抓取任务执行成功' if result.get('success') else '任务执行失败'
            }, ensure_ascii=False)
        }

        logger.info(f"Serverless函数执行完成: {response['body']}")
        return response

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Serverless函数执行失败: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': '任务执行失败'
            }, ensure_ascii=False)
        }


# AWS Lambda入口
def lambda_handler(event, context):
    """AWS Lambda处理器"""
    return handler(event, context)


# 阿里云函数计算入口
def aliyun_handler(event, context):
    """阿里云函数计算处理器"""
    return handler(event, context)


# 腾讯云函数入口
def tencent_handler(event, context):
    """腾讯云SCF处理器"""
    return handler(event, context)


# 本地测试入口
if __name__ == '__main__':
    # 用于本地测试
    result = handler({}, {})
    print(json.dumps(result, indent=2, ensure_ascii=False))