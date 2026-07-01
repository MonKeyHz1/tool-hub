"""MIP 海关清关工具 - 工具包装器，实现 BaseTool 接口。

前端通过此工具上传 Excel 文件并批量导入海关清关数据。
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from ...models import ToolMeta, ToolResult
from ..base import BaseTool
from .client import MIPAsyncClient
from .config import MIPConfig
from .excel_import import ExcelImporter
from .import_config import ImportDefaults
from .import_state import ImportState
from .import_task import ImportTaskManager, ImportTaskStatus

logger = structlog.get_logger()


class MIPCustomsTool(BaseTool):
    """MIP 海关清关 Excel 批量导入工具。

    功能：
    - 上传 Excel 文件（含运单号、商品、收货人等数据）
    - 执行批量导入并返回详细结果
    - 创建（POST）和更新（PUT）拆分为两个独立工具
    """

    tool_id = ""           # 子类或实例覆盖
    tool_name = ""         # 子类或实例覆盖
    tool_description = ""  # 子类或实例覆盖

    def __init__(self, use_create: bool = True, tool_id: str = "", tool_name: str = "", hidden: bool = False) -> None:
        """初始化工具。

        Args:
            use_create: True=创建模式(POST), False=更新模式(PUT)。
            tool_id: 工具唯一标识。
            tool_name: 工具显示名称。
            hidden: 是否在主页隐藏。
        """
        super().__init__()
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.tool_description = (
            f"上传 Excel 文件，批量{tool_name}海关清关申报数据到 MIP API"
        )
        self._use_create = use_create
        self._hidden = hidden

    def get_meta(self) -> ToolMeta:
        """返回工具的元信息供前端展示。"""
        return ToolMeta(
            tool_id=self.tool_id,
            tool_name=self.tool_name,
            description=self.tool_description,
            version="0.1.0",
            requires_file=True,
            accepted_file_types=[".xlsx", ".xls"],
            hidden=self._hidden,
            input_schema={
                "type": "object",
                "properties": {
                    "token_env": {
                        "type": "string",
                        "enum": ["test", "prod"],
                        "default": "test",
                        "description": "Token 环境：test=测试, prod=生产",
                    },
                },
            },
        )

    async def execute(
        self,
        params: dict[str, Any],
        file_path: Path | None = None,
        request_host: str = "",
    ) -> ToolResult:
        """启动异步 Excel 导入任务并立即返回 task_id。

        前端拿到 task_id 后通过 /api/mip-customs/status/{task_id} 轮询进度，
        避免大文件导入触发网关/前端超时。
        """
        if file_path is None:
            return ToolResult(
                success=False,
                message="请先上传 Excel 文件",
                errors=[{"error_type": "NO_FILE", "message": "未上传文件"}],
            )

        if not file_path.exists():
            return ToolResult(
                success=False,
                message=f"文件不存在: {file_path}",
                errors=[{"error_type": "FILE_NOT_FOUND", "message": f"文件不存在: {file_path}"}],
            )

        manager = ImportTaskManager()
        task = await manager.create_task()

        # 启动后台任务
        asyncio.create_task(self._run_import_task(task.task_id, params, file_path))

        return ToolResult(
            success=True,
            message="导入任务已启动",
            data={
                "task_id": task.task_id,
                "mode": "创建" if self._use_create else "更新",
                "status_url": f"/api/mip-customs/status/{task.task_id}",
            },
        )

    async def _run_import_task(
        self,
        task_id: str,
        params: dict[str, Any],
        file_path: Path,
    ) -> None:
        """实际执行导入的后台任务。"""
        manager = ImportTaskManager()
        started_at = datetime.now(UTC).isoformat()

        try:
            await manager.update_task(
                task_id,
                status=ImportTaskStatus.PARSING,
                message="正在解析 Excel 文件",
            )

            # 1. 构建导入默认值配置
            defaults = ImportDefaults(
                sender_country_code=params.get("sender_country_code", "CN"),
                sender_country_name=params.get("sender_country_name", "CHINA"),
                sender_nationality=params.get("sender_nationality", "CNN"),
                sender_name_1=params.get("sender_name_1", ""),
                sender_name_2=params.get("sender_name_2", ""),
                sender_address=params.get("sender_address", ""),
                sender_telephone=params.get("sender_telephone", ""),
                price=__import__("decimal").Decimal(params.get("price", "0.00")),
                price_currency=params.get("price_currency", "RMB"),
            )

            # 2. 初始化导入状态（不再每次自动清理）
            state = ImportState()

            # 3. 初始化 MIP 异步客户端（根据 token_env 选择 token）
            config = MIPConfig()
            token_env = params.get("token_env", "test")
            if token_env == "prod":
                config.access_token = config.access_token_prod
            else:
                config.access_token = config.access_token_test or config.access_token

            async with MIPAsyncClient(config) as client:
                # 4. 创建导入器并执行
                importer = ExcelImporter(
                    client=client,
                    defaults=defaults,
                    state=state,
                    use_create_api=self._use_create,
                    progress_callback=manager.make_progress_callback(task_id),
                    task_manager=manager,
                    task_id=task_id,
                )

                batch = await importer.import_file(file_path)

            completed_at = datetime.now(UTC).isoformat()

            # 5. 构建返回结果
            success = batch.failure_count == 0
            message = (
                f"导入完成: {batch.success_count}/{batch.processed_rows} 成功"
            )
            if batch.failure_count > 0:
                message += f", {batch.failure_count} 失败"

            await manager.update_task(
                task_id,
                status=ImportTaskStatus.COMPLETED,
                message=message,
                result={
                    "success": success,
                    "source_file": batch.source_file,
                    "total_rows": batch.total_rows,
                    "processed_rows": batch.processed_rows,
                    "success_count": batch.success_count,
                    "failure_count": batch.failure_count,
                    "mode": "创建" if self._use_create else "更新",
                    "started_at": started_at,
                    "completed_at": completed_at,
                },
                errors=[
                    {
                        "row_number": e.row_number,
                        "tracking_number": e.tracking_number,
                        "error_type": e.error_type,
                        "message": e.message,
                    }
                    for e in batch.errors
                ],
            )

        except Exception as exc:
            self._logger.exception("tool_execution_failed", task_id=task_id, error=str(exc))
            await manager.update_task(
                task_id,
                status=ImportTaskStatus.FAILED,
                message=f"执行失败: {exc}",
                errors=[{"error_type": "EXECUTION_ERROR", "message": str(exc)}],
            )
