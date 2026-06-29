"""结构化日志配置，复用原项目的 PII 脱敏逻辑。"""

import logging
import re
from collections.abc import MutableMapping
from typing import Any

import structlog

# 需要脱敏的字段名
SENSITIVE_FIELDS = {
    "password",
    "token",
    "api_key",
    "secret",
    "authorization",
    "access_token",
}

# 电话号码正则
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-\(\)]{7,}")


def redact_sensitive_fields(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """脱敏处理：将敏感字段替换为 ***REDACTED***。"""
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_FIELDS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def setup_logging() -> None:
    """初始化结构化日志系统。"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            redact_sensitive_fields,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
