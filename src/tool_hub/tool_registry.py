"""工具注册中心 - 管理所有已注册的工具。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from .tools.base import BaseTool

logger = structlog.get_logger()


class ToolRegistry:
    """工具注册中心（单例模式）。

    负责管理所有工具的注册、查找和列表展示。
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}  # type: ignore[name-defined]
        self._logger = logger.bind(component="ToolRegistry")

    def register(self, tool: BaseTool) -> None:
        """注册一个工具实例。

        Args:
            tool: 继承 BaseTool 的工具实例。

        Raises:
            ValueError: 如果 tool_id 重复。
        """
        tool_id = tool.tool_id
        if tool_id in self._tools:
            raise ValueError(f"工具 '{tool_id}' 已经注册过了")
        self._tools[tool_id] = tool
        self._logger.info("tool_registered", tool_id=tool_id, tool_name=tool.tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        """列出所有已注册工具的基本信息。

        Returns:
            工具信息列表，每个元素包含 id、name、description 等字段。
        """
        result: list[dict[str, Any]] = []
        for t in self._tools.values():
            meta = t.get_meta()
            if meta.hidden:
                continue
            result.append(
                {
                    "tool_id": meta.tool_id,
                    "tool_name": meta.tool_name,
                    "description": meta.description,
                    "version": meta.version,
                    "requires_file": meta.requires_file,
                    "accepted_file_types": meta.accepted_file_types,
                    "input_schema": meta.input_schema,
                }
            )
        return result

    def get_tool(self, tool_id: str) -> BaseTool | None:
        """根据 tool_id 获取工具实例。

        Args:
            tool_id: 工具唯一标识。

        Returns:
            工具实例，不存在则返回 None。
        """
        return self._tools.get(tool_id)

    @property
    def tool_count(self) -> int:
        """已注册的工具数量。"""
        return len(self._tools)
