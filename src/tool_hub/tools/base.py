"""工具基类 - 所有工具必须继承此类并实现抽象方法。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

from ..models import ToolMeta, ToolResult

logger = structlog.get_logger()


class BaseTool(ABC):
    """工具基类。

    每种工具都是一个独立的 Python 包，放在 tools/ 目录下。
    工具的模块中必须定义一个继承 BaseTool 的类，并在包的
    __init__.py 中导出。
    """

    # 子类必须覆盖这些类属性
    tool_id: str = ""                     # 唯一标识
    tool_name: str = ""                   # 显示名称
    tool_description: str = ""            # 功能描述

    def __init__(self) -> None:
        self._logger = logger.bind(tool_id=self.tool_id)

    @abstractmethod
    def get_meta(self) -> ToolMeta:
        """返回工具的元信息。

        子类需要返回一个 ToolMeta 实例，包含工具名称、描述、
        是否需要上传文件、支持的文件类型等。
        """
        ...

    @abstractmethod
    async def execute(
        self,
        params: dict[str, Any],
        file_path: Path | None = None,
        request_host: str = "",
    ) -> ToolResult:
        """执行工具。

        Args:
            params: 执行参数（键值对）。
            file_path: 上传的文件路径（如果需要文件输入）。
            request_host: 请求 Host，用于生成下载链接等场景。

        Returns:
            ToolResult 包含执行结果、成功/失败状态、错误信息等。
        """
        ...
