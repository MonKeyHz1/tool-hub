"""统一错误响应工具。

为所有工具路由提供标准化的异常转换，避免每个 router 都返回
{success: False, message: str(e)}，让前端可以根据 error_code 快速分类。
"""

from __future__ import annotations

from typing import Any

import httpx

ERROR_TIMEOUT = "TIMEOUT_ERROR"
ERROR_AUTH = "AUTH_ERROR"
ERROR_VALIDATION = "VALIDATION_ERROR"
ERROR_BUSINESS = "BUSINESS_ERROR"
ERROR_UNKNOWN = "UNKNOWN_ERROR"


def classify_exception(exc: BaseException) -> tuple[str, str]:
    """将异常分类为 error_code 和 message。

    Returns:
        (error_code, message)
    """
    if isinstance(exc, httpx.TimeoutException):
        return ERROR_TIMEOUT, f"请求超时: {exc}"
    if isinstance(exc, httpx.NetworkError):
        return ERROR_TIMEOUT, f"网络错误: {exc}"
    message = str(exc)
    lowered = message.lower()
    if "unauthorized" in lowered or "认证失败" in message or "auth" in lowered:
        return ERROR_AUTH, message
    if "validation" in lowered or "invalid" in lowered or "参数" in message:
        return ERROR_VALIDATION, message
    return ERROR_BUSINESS, message


def error_response(exc: BaseException) -> dict[str, Any]:
    """生成统一的错误响应字典。

    返回结构:
        {
            "success": False,
            "error_code": "TIMEOUT_ERROR" | "AUTH_ERROR" | ...,
            "message": "...",
        }
    """
    code, message = classify_exception(exc)
    return {"success": False, "error_code": code, "message": message}
