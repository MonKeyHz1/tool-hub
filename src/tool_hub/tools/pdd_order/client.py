"""PDD 下单异步 HTTP 客户端。"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from .config import PDDOrderConfig
from .sign_utils import sign_pdd

logger = structlog.get_logger()


class PDDOrderClient:
    """PDD 集运下单客户端。"""

    def __init__(self, config: PDDOrderConfig | None = None) -> None:
        self.config = config or PDDOrderConfig()
        import os
        to = float(os.environ.get("TIMEOUT", "120"))
        self._client = httpx.AsyncClient(
            base_url=self.config.gateway_url,
            timeout=httpx.Timeout(to, connect=to, read=to, write=to, pool=to),
        )
        print(f"[PDD] timeout={to}")
        self._logger = logger.bind(component="PDDOrderClient")

    async def create_order(self, body: dict[str, Any]) -> dict[str, Any]:
        print("[PDD STEP1] enter")
        sign = sign_pdd(body, self.config.client_secret)
        print("[PDD STEP2] sign")
        body_with_sign = {**body, "sign": sign}
        body_json = json.dumps(body_with_sign, ensure_ascii=False, separators=(",", ":"))
        print(f"[PDD STEP3] sign={sign} body_len={len(body_json)}")
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        print("[PDD STEP4] post")
        try:
            resp = await self._client.post(
                "/api/pdd/callback/conso/order/create",
                content=body_json.encode("utf-8"),
                headers=headers,
            )
        except httpx.TimeoutException as e:
            print(f"[PDD STEP5] TIMEOUT after {self._client.timeout.read}s")
            raise
        except httpx.HTTPError as e:
            print(f"[PDD STEP5] HTTP_ERROR {type(e).__name__}: {e}")
            raise
        print(f"[PDD STEP5] resp={resp.status_code}")
        result = resp.json()
        print(f"[PDD STEP6] result={result}")
        return result

    async def close(self) -> None:
        """关闭 HTTP 客户端。"""
        await self._client.aclose()

    async def __aenter__(self) -> "PDDOrderClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
