"""推送重量工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ...models import ToolMeta, ToolResult
from ..base import BaseTool

logger = structlog.get_logger()


class PushWeightTool(BaseTool):
    """推送重量工具。

    查询快递单号对应的尾程单号，推送到 TMS 生产环境修复"无法出库"问题。
    涉及生产环境操作，使用前需要二次确认。
    """

    tool_id = "push_weight"
    tool_name = "推送重量"
    tool_description = "查询快递单号获取尾程单号，推送重量到 TMS 生产环境修复无法出库问题（需谨慎操作）"

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
    ) -> ToolResult:
        return ToolResult(
            success=True,
            message="推送重量工具已就绪，请使用专用 API 接口操作",
        )
