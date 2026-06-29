"""工具中心 - 启动入口。

运行方式:
    # 安装依赖
    uv sync

    # 启动服务
    uv run python main.py

    # 或开发模式
    uv run uvicorn tool_hub.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn

from tool_hub.config import settings


def main() -> None:
    """启动 FastAPI 服务。"""
    uvicorn.run(
        "tool_hub.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
