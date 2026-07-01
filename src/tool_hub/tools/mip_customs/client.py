"""异步 MIP 海关清关 API 客户端。

基于原项目的 async_client.py 改造，聚焦于工具需要的接口。
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog

from .config import MIPConfig
from .exceptions import (
    MIPAPIError,
    MIPAuthError,
    MIPDuplicateError,
    MIPNotFoundError,
    MIPValidationError,
)
from .models import CustomsItem

logger = structlog.get_logger()


class MIPAsyncClient:
    """异步 MIP 海关清关 API 客户端。

    封装了 create_item 和 update_item 两个核心接口，
    支持自动认证和错误处理。
    """

    def __init__(self, config: MIPConfig | None = None, request_timeout: float | None = None) -> None:
        """初始化异步客户端。

        Args:
            config: MIP API 配置，不传则从环境变量加载。
            request_timeout: 单个请求超时（秒），覆盖 config.timeout。
        """
        self.config = config or MIPConfig()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=request_timeout if request_timeout is not None else self.config.timeout,
        )
        self._logger = logger.bind(client="MIPAsyncClient")

    def _get_auth_headers(self) -> dict[str, str]:
        """获取认证请求头。

        Returns:
            包含 accesstoken 的请求头字典。
        """
        if self.config.access_token:
            return {"accesstoken": self.config.access_token}
        return {}

    async def _make_request(
        self,
        method: str,
        path: str,
        trace_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """发送 HTTP 请求并处理错误。

        Args:
            method: HTTP 方法（GET/POST/PUT 等）。
            path: API 路径。
            trace_id: 追踪 ID（用于日志关联）。

        Returns:
            API 响应的 JSON 字典。

        Raises:
            MIPAuthError: 认证失败。
            MIPNotFoundError: 资源不存在。
            MIPDuplicateError: 数据重复。
            MIPValidationError: 参数校验失败。
            MIPAPIError: 其他 API 错误。
        """
        log = self._logger.bind(trace_id=trace_id, method=method, path=path)
        log.info("mip_request_start")

        # 合并认证请求头
        headers = self._get_auth_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            response = await self._client.request(method, path, headers=headers, **kwargs)
            log.info("mip_request_complete", status_code=response.status_code)
        except httpx.TimeoutException as e:
            log.error("mip_request_timeout", error=str(e))
            raise MIPAPIError(f"Request timeout: {e}", status_code=408) from e
        except httpx.HTTPError as e:
            log.error("mip_request_error", error=str(e))
            raise MIPAPIError(f"HTTP error: {e}") from e

        # 处理错误状态码
        if response.status_code >= 400:
            self._handle_error(response)

        result: dict[str, Any] = response.json()
        return result

    def _handle_error(self, response: httpx.Response) -> None:
        """根据 HTTP 状态码抛出对应的异常。

        Args:
            response: HTTP 响应对象。

        Raises:
            对应的 MIP 异常子类。
        """
        try:
            data = response.json()
            message = data.get("message", "Unknown error")
        except Exception:
            message = response.text or "Unknown error"

        if response.status_code == 401:
            raise MIPAuthError(message)
        elif response.status_code == 404:
            raise MIPNotFoundError(message)
        elif response.status_code == 500 and "already exists" in message.lower():
            raise MIPDuplicateError(message)
        elif response.status_code == 400:
            raise MIPValidationError(message)
        elif response.status_code == 500:
            raise MIPAPIError(message, status_code=500)
        else:
            raise MIPAPIError(message, status_code=response.status_code)

    async def create_item(self, item: CustomsItem) -> dict[str, Any]:
        """创建海关清关申报单（POST）。

        Args:
            item: 海关清关申报数据模型。

        Returns:
            API 响应的 JSON 数据。
        """
        trace_id = str(uuid.uuid4())
        payload = item.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._make_request(
            "POST",
            "/order_api/api/customs/temu",
            trace_id=trace_id,
            json=payload,
        )
        return data

    async def update_item(self, item: CustomsItem) -> dict[str, Any]:
        """更新海关清关申报单（PUT）。

        Args:
            item: 海关清关申报数据模型。

        Returns:
            API 响应的 JSON 数据。
        """
        trace_id = str(uuid.uuid4())
        payload = item.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._make_request(
            "PUT",
            f"/order_api/api/customs/temu/{item.tracking_number}",
            trace_id=trace_id,
            json=payload,
        )
        return data

    async def close(self) -> None:
        """关闭 HTTP 客户端连接。"""
        await self._client.aclose()

    async def __aenter__(self) -> "MIPAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
