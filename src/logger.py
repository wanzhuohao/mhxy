"""日志：写入 logs/mhxy.log（按天滚动），不输出到控制台"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

# 日志目录：mhxy/logs/
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

_logger = logging.getLogger('mhxy')
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    _handler = TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, 'mhxy.log'),
        when='midnight', backupCount=3, encoding='utf-8')
    _handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
    _logger.addHandler(_handler)


def log(msg, level=""):
    """带时间戳的日志。

    level 映射：
    - "" 或未传 → INFO
    - "WARN" → WARNING
    - "ERR" → ERROR
    - 其他非空值（如"点"）→ 作为消息标签，按 INFO 记录
    """
    if level == "WARN":
        _logger.warning(msg)
    elif level == "ERR":
        _logger.error(msg)
    elif level:
        _logger.info(f"[{level}] {msg}")
    else:
        _logger.info(msg)
