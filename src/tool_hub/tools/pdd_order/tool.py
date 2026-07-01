"""PDD 集运下单工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ...models import ToolMeta, ToolResult
from ..base import BaseTool

logger = structlog.get_logger()


class PDDOrderTool(BaseTool):
    """PDD 集运下单工具。

    支持上门（homeDelivery）和自提（selfPickup）两种配送方式。
    后端自动生成动态字段（物流单号、运单号、买家编码等）并计算 MD5 签名。
    """

    tool_id = "pdd_order"
    tool_name = "PDD-MN流程"
    tool_description = (
        "PDD Gateway 集运订单创建工具。支持上门/自提两种配送方式，"
        "自动生成动态字段和 MD5 签名。")

    def get_meta(self) -> ToolMeta:
        return ToolMeta(
            tool_id=self.tool_id,
            tool_name=self.tool_name,
            description=self.tool_description,
            version="0.1.0",
            requires_file=False,
            accepted_file_types=[],
            input_schema={"type": "object", "properties": {}},
        )

    async def execute(
        self,
        params: dict[str, Any],
        file_path: Path | None = None,
        request_host: str = "",
    ) -> ToolResult:
        return ToolResult(
            success=True,
            message="PDD 集运下单工具已就绪，请使用专用 API 接口操作",
        )
