"""Temu 网关异步 HTTP 客户端。"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import structlog

from .config import TemuGatewayConfig
from .crypto_utils import generate_secret, generate_sign

logger = structlog.get_logger()


class TemuGatewayClient:
    """Temu 网关异步客户端，封装登录、下单、面单查询三个接口。"""

    def __init__(self, config=None, base_url: str = "") -> None:
        """初始化客户端。

        Args:
            config: Temu 网关配置，不传则从环境变量加载。
        """
        self.config = config or TemuGatewayConfig()
        self._base_url = base_url or self.config.gateway_url
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self.config.timeout,
        )
        self._logger = logger.bind(component="TemuGatewayClient")

    async def login(self, app_id: str, app_secret: str) -> dict[str, Any]:
        """登录获取 password。

        Args:
            app_id: 应用 ID。
            app_secret: Base64 编码的 AES 密钥。

        Returns:
            包含 password 和 exp 的字典。

        Raises:
            RuntimeError: 登录失败。
        """
        self._logger.info("temu_login_start", app_id=app_id)
        secret = generate_secret(app_id, app_secret)
        resp = await self._client.post(
            "/auth/api/login",
            json={"appId": app_id, "secret": secret},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"登录失败: {data}")
        result = {
            "password": data["data"]["password"],
            "exp": data["data"].get("exp", 0),
        }
        self._logger.info("temu_login_success", exp=result["exp"])
        return result

    async def place_order(
        self, app_id: str, password: str, order_body: dict[str, Any]
    ) -> dict[str, Any]:
        """下单。

        Args:
            app_id: 应用 ID。
            password: 登录返回的 password。
            order_body: 订单数据。

        Returns:
            API 响应 JSON。
        """
        ts = str(int(time.time()))
        body_str = json.dumps(order_body, ensure_ascii=False, separators=(",", ":"))
        sign = generate_sign(body_str, password, ts)

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "appId": app_id,
            "timestamp": ts,
            "Authorization": sign,
        }

        self._logger.info(
            "temu_place_order_start",
            order_number=order_body.get("orderNumber", ""),
        )
        resp = await self._client.post(
            "/temu/api/logistics/order",
            content=body_str.encode("utf-8"),
            headers=headers,
        )
        return resp.json()

    async def get_express_sheet(
        self, app_id: str, password: str, reference_no: str
    ) -> dict[str, Any]:
        """查询标准面单。

        Args:
            app_id: 应用 ID。
            password: 登录返回的 password。
            reference_no: 订单号。

        Returns:
            API 响应 JSON，包含 sheetData 字段（Base64 编码的 PDF）。
        """
        ts = str(int(time.time()))
        sign = generate_sign("", password, ts)

        headers = {
            "appId": app_id,
            "timestamp": ts,
            "Authorization": sign,
        }

        self._logger.info("temu_express_sheet_start", reference_no=reference_no)
        resp = await self._client.get(
            "/temu/api/logistics/express-sheet",
            params={"referenceNo": reference_no},
            headers=headers,
        )
        return resp.json()

    async def get_last_mile_sheet(
        self, app_id: str, password: str, waybill_no: str, reference_no: str
    ) -> dict[str, Any]:
        """查询尾程面单。

        Args:
            app_id: 应用 ID。
            password: 登录返回的 password。
            waybill_no: 运单号。
            reference_no: 订单号。

        Returns:
            API 响应 JSON。
        """
        ts = str(int(time.time()))
        sign = generate_sign("", password, ts)

        headers = {
            "appId": app_id,
            "timestamp": ts,
            "Authorization": sign,
        }

        self._logger.info(
            "temu_last_mile_sheet_start",
            waybill_no=waybill_no,
            reference_no=reference_no,
        )
        resp = await self._client.get(
            "/temu/api/logistics/last-mile-sheet",
            params={"waybillNo": waybill_no, "referenceNo": reference_no},
            headers=headers,
        )
        return resp.json()

    async def close(self) -> None:
        """关闭 HTTP 客户端连接。"""
        await self._client.aclose()

    async def __aenter__(self) -> "TemuGatewayClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
