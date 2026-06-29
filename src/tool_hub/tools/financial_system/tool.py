"""财务系统工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ...models import ToolMeta, ToolResult
from ..base import BaseTool

logger = structlog.get_logger()


class FinancialSystemTool(BaseTool):
    """财务系统工具。

    集成 TMS 财务相关接口，支持登录后调用任意 API，
    自动保存/恢复请求 JSON，方便测试造数据。
    """

    tool_id = "financial_system"
    tool_name = "财务系统"
    tool_description = "集成 TMS 财务相关接口（增改），支持登录鉴权、保存/恢复请求 JSON、测试造数据"

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
            message="财务系统工具已就绪，请使用专用 API 接口操作",
        )
