"""
工具函数模块
提供日志配置、通知发送等辅助功能
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import colorlog
import time
import json


def setup_logging(config: Dict[str, Any]) -> None:
    """
    配置日志系统

    Args:
        config: 日志配置字典
    """
    log_level = config.get('level', 'INFO')
    log_file = config.get('file', './logs/arxiv_scraper.log')
    console_output = config.get('console', True)
    max_size = config.get('max_size', 10) * 1024 * 1024  # MB to bytes
    backup_count = config.get('backup_count', 5)

    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))

    # 清除现有的处理器
    logger.handlers.clear()

    # 文件处理器（带日志轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台处理器（带颜色）
    if console_output:
        console_handler = colorlog.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)


def create_retry_session(
    total_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Optional[List[int]] = None,
    allowed_methods: Optional[List[str]] = None
) -> requests.Session:
    """
    创建带重试机制的 requests Session

    Args:
        total_retries: 总重试次数
        backoff_factor: 退避系数（用于指数退避）
        status_forcelist: 需要重试的状态码列表
        allowed_methods: 允许重试的 HTTP 方法列表

    Returns:
        配置好重试策略的 Session
    """
    session = requests.Session()
    status_forcelist = status_forcelist or [429, 500, 502, 503, 504]
    allowed_methods = allowed_methods or ["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]

    retry_kwargs = dict(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )

    try:
        retry = Retry(**retry_kwargs, allowed_methods=frozenset(allowed_methods))
    except TypeError:
        retry = Retry(**retry_kwargs, method_whitelist=frozenset(allowed_methods))

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def send_notification(config: Dict[str, Any], message: str, subject: str = None) -> bool:
    """
    发送通知

    Args:
        config: 通知配置字典
        message: 通知消息内容
        subject: 通知主题（邮件标题）

    Returns:
        是否发送成功
    """
    if not config.get('enabled', False):
        return True  # 未启用通知，视为成功

    method = config.get('method', 'email')

    try:
        if method == 'email':
            return _send_email(config.get('email', {}), message, subject)
        elif method == 'webhook':
            return _send_webhook(config.get('webhook', {}), message, subject)
        else:
            logging.warning(f"不支持的通知方式: {method}")
            return False

    except Exception as e:
        logging.error(f"发送通知失败: {str(e)}")
        return False


def _send_email(config: Dict[str, Any], message: str, subject: str = None) -> bool:
    """
    通过邮件发送通知

    Args:
        config: 邮件配置
        message: 邮件内容
        subject: 邮件主题

    Returns:
        是否发送成功
    """
    smtp_server = config.get('smtp_server')
    smtp_port = config.get('smtp_port', 587)
    sender = config.get('sender')
    password = config.get('password')
    recipients = config.get('recipients', [])

    if not all([smtp_server, sender, password, recipients]):
        logging.error("邮件配置不完整")
        return False

    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject or 'ArXiv 论文抓取通知'

        # 添加邮件正文
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        # 连接 SMTP 服务器并发送（设置30秒超时）
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        logging.info("邮件通知发送成功")
        return True

    except smtplib.SMTPException as e:
        logging.error(f"SMTP 错误: {str(e)}")
        return False
    except TimeoutError as e:
        logging.error(f"连接超时: {str(e)}")
        logging.error("请检查: 1) SMTP服务器地址和端口是否正确 2) 网络连接是否正常 3) 防火墙设置")
        return False
    except Exception as e:
        logging.error(f"发送邮件失败: {str(e)}")
        return False


def _send_webhook(config: Dict[str, Any], message: str, subject: str = None) -> bool:
    """
    通过 Webhook 发送通知

    Args:
        config: Webhook 配置
        message: 消息内容
        subject: 消息主题

    Returns:
        是否发送成功
    """
    url = config.get('url')
    method = config.get('method', 'POST').upper()

    if not url:
        logging.error("Webhook URL 未配置")
        return False

    try:
        payload = {
            'subject': subject or 'ArXiv 论文抓取通知',
            'message': message
        }

        if method == 'POST':
            response = requests.post(url, json=payload, timeout=10)
        elif method == 'GET':
            response = requests.get(url, params=payload, timeout=10)
        else:
            logging.error(f"不支持的 HTTP 方法: {method}")
            return False

        response.raise_for_status()
        logging.info("Webhook 通知发送成功")
        return True

    except Exception as e:
        logging.error(f"发送 Webhook 通知失败: {str(e)}")
        return False


def format_paper_summary(papers: list) -> str:
    """
    格式化论文摘要信息

    Args:
        papers: 论文列表

    Returns:
        格式化后的摘要文本
    """
    if not papers:
        return "本次未抓取到新论文。"

    lines = [f"成功抓取 {len(papers)} 篇论文：\n"]

    for i, paper in enumerate(papers[:10], 1):  # 只显示前10篇
        title = paper.get('title', 'N/A')
        authors = paper.get('authors', [])
        author_str = ', '.join(authors[:3])  # 只显示前3位作者
        if len(authors) > 3:
            author_str += ' et al.'

        lines.append(f"{i}. {title}")
        lines.append(f"   作者: {author_str}")
        lines.append("")

    if len(papers) > 10:
        lines.append(f"... 以及其他 {len(papers) - 10} 篇论文")

    return '\n'.join(lines)


def validate_config_file(config_path: str) -> bool:
    """
    验证配置文件是否存在且有效

    Args:
        config_path: 配置文件路径

    Returns:
        是否有效
    """
    if not os.path.exists(config_path):
        logging.error(f"配置文件不存在: {config_path}")
        return False

    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if config is None:
            logging.error("配置文件为空")
            return False

        return True

    except Exception as e:
        logging.error(f"配置文件无效: {str(e)}")
        return False


def ensure_directories(config: Dict[str, Any]) -> None:
    """
    确保必要的目录存在

    Args:
        config: 配置字典
    """
    storage_config = config.get('storage', {})
    logging_config = config.get('logging', {})

    # 数据目录
    data_dir = storage_config.get('data_dir', './data/papers')
    os.makedirs(data_dir, exist_ok=True)

    # 缓存目录
    cache_file = storage_config.get('cache_file')
    if storage_config.get('cache_enabled', True) and cache_file:
        cache_dir = os.path.dirname(cache_file)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # PDF 目录
    if storage_config.get('download_pdf', False):
        pdf_dir = storage_config.get('pdf_dir', './data/pdfs')
        os.makedirs(pdf_dir, exist_ok=True)

    # 日志目录
    log_file = logging_config.get('file', './logs/arxiv_scraper.log')
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)


def send_email_with_attachments(
    config: Dict[str, Any],
    message: str,
    subject: str,
    attachments: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    发送带附件的邮件

    Args:
        config: 邮件配置
        message: 邮件正文
        subject: 邮件主题
        attachments: 附件列表，每个附件是一个字典:
                    {'file_path': '文件路径', 'filename': '附件名称（可选）'}

    Returns:
        是否发送成功
    """
    smtp_server = config.get('smtp_server')
    smtp_port = config.get('smtp_port', 587)
    sender = config.get('sender')
    password = config.get('password')
    recipients = config.get('recipients', [])

    if not all([smtp_server, sender, password, recipients]):
        logging.error("邮件配置不完整")
        return False

    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject

        # 添加邮件正文
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        # 添加附件
        if attachments:
            for attachment_info in attachments:
                file_path = attachment_info.get('file_path')
                if not file_path or not os.path.exists(file_path):
                    logging.warning(f"附件文件不存在: {file_path}")
                    continue

                # 读取文件
                with open(file_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())

                # 编码附件
                encoders.encode_base64(part)

                # 设置附件文件名
                filename = attachment_info.get('filename') or os.path.basename(file_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )

                msg.attach(part)

                logging.info(f"已添加附件: {filename}")

        # 连接 SMTP 服务器并发送（设置30秒超时）
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        logging.info("带附件的邮件发送成功")
        return True

    except smtplib.SMTPException as e:
        logging.error(f"SMTP 错误: {str(e)}")
        return False
    except TimeoutError as e:
        logging.error(f"连接超时: {str(e)}")
        logging.error("请检查: 1) SMTP服务器地址和端口是否正确 2) 网络连接是否正常 3) 防火墙设置")
        return False
    except Exception as e:
        logging.error(f"发送带附件邮件失败: {str(e)}")
        return False


def send_email_with_retry(
    config: Dict[str, Any],
    message: str,
    subject: str,
    attachments: Optional[List[Dict[str, str]]] = None,
    max_retries: int = 3,
    retry_delay: int = 5
) -> bool:
    """
    发送带附件的邮件（带重试机制）

    Args:
        config: 邮件配置
        message: 邮件正文
        subject: 邮件主题
        attachments: 附件列表
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）

    Returns:
        是否发送成功
    """
    for attempt in range(1, max_retries + 1):
        logging.info(f"尝试发送邮件 (第 {attempt}/{max_retries} 次)...")

        success = send_email_with_attachments(config, message, subject, attachments)

        if success:
            return True

        if attempt < max_retries:
            logging.warning(f"邮件发送失败，{retry_delay} 秒后重试...")
            time.sleep(retry_delay)
        else:
            logging.error(f"邮件发送失败，已达到最大重试次数 ({max_retries})")

    return False


def send_report_via_webhook(
    webhook_config: Dict[str, Any],
    report_content: str,
    paper_count: int,
    timestamp: str
) -> bool:
    """
    通过Webhook发送报告内容

    Args:
        webhook_config: Webhook配置
        report_content: 报告内容（Markdown格式）
        paper_count: 论文数量
        timestamp: 生成时间戳

    Returns:
        是否发送成功
    """
    url = webhook_config.get('url')
    method = webhook_config.get('method', 'POST').upper()

    if not url:
        logging.error("Webhook URL 未配置")
        return False

    try:
        payload = {
            'type': 'arxiv_report',
            'timestamp': timestamp,
            'paper_count': paper_count,
            'content': report_content,
            'format': 'markdown'
        }

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ArXiv-Paper-Agent/1.0'
        }

        if method == 'POST':
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, json=payload, headers=headers, timeout=30)
        else:
            logging.error(f"不支持的 HTTP 方法: {method}")
            return False

        response.raise_for_status()
        logging.info(f"报告已通过 Webhook 发送成功 (状态码: {response.status_code})")
        return True

    except requests.exceptions.Timeout:
        logging.error("Webhook 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Webhook 请求失败: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"发送 Webhook 失败: {str(e)}")
        return False
