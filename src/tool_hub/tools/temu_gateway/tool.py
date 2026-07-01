"""Temu Gateway 工具 - 工具包装器，实现 BaseTool 接口。

提供 Temu 网关的鉴权、下单、面单查询功能。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ...models import ToolMeta, ToolResult
from ..base import BaseTool

logger = structlog.get_logger()


class TemuGatewayTool(BaseTool):
    """Temu 网关工具，提供鉴权、下单、面单查询功能。

    登录获取鉴权密码后，可用于下单和查询面单。
    """

    tool_id = "temu_gateway"
    tool_name = "Temu网关"
    tool_description = (
        "Temu 网关 API 工具：支持登录鉴权（生成加密签名参数）、"
        "下单（POST /logistics/order）和获取面单（GET /express-sheet）"
    )

    def get_meta(self) -> ToolMeta:
        """返回工具的元信息供前端展示。"""
        return ToolMeta(
            tool_id=self.tool_id,
            tool_name=self.tool_name,
            description=self.tool_description,
            version="0.1.0",
            requires_file=False,
            accepted_file_types=[],
            input_schema={
                "type": "object",
                "properties": {},
            },
        )

    async def execute(
        self,
        params: dict[str, Any],
        file_path: Path | None = None,
        request_host: str = "",
    ) -> ToolResult:
        """Temu Gateway 工具不需要通用执行入口，
        实际操作通过专属 API 路由完成。
        """
        return ToolResult(
            success=True,
            message="Temu 网关工具已就绪，请使用专用 API 接口操作",
        )
