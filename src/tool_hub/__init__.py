"""工具中心 - 集成多个业务工具的后端服务。"""

from .tool_registry import ToolRegistry

# 全局工具注册中心（单例）
registry = ToolRegistry()

__version__ = "0.1.0"

__all__ = ["registry"]
