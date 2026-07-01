"""MIP 导入异步任务管理器。

支持启动后台 Excel 导入任务并轮询进度，避免大文件导入触发前端/网关超时。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class ImportTaskStatus(str, Enum):
    """任务状态。"""

    PENDING = "pending"
    PARSING = "parsing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ImportTask:
    """单个导入任务的状态。"""

    task_id: str
    status: ImportTaskStatus = ImportTaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    progress: int = 0
    total: int = 0
    message: str = "等待开始"
    result: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "result": self.result,
            "errors": self.errors,
        }


ProgressCallback = Callable[[int, int, str], None]


class ImportTaskManager:
    """MIP 导入任务管理器（单例，内存存储）。"""

    _instance: ImportTaskManager | None = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> ImportTaskManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: dict[str, ImportTask] = {}
            cls._instance._logger = logger.bind(component="ImportTaskManager")
            cls._lock = asyncio.Lock()
        return cls._instance

    async def create_task(self) -> ImportTask:
        task = ImportTask(task_id=uuid.uuid4().hex[:16])
        async with self._lock:
            self._tasks[task.task_id] = task
        return task

    async def get_task(self, task_id: str) -> ImportTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(
        self,
        task_id: str,
        status: ImportTaskStatus | None = None,
        progress: int | None = None,
        total: int | None = None,
        message: str | None = None,
        result: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            if status is not None:
                task.status = status
                if status == ImportTaskStatus.RUNNING and task.started_at is None:
                    task.started_at = datetime.now(UTC).isoformat()
                if status in (ImportTaskStatus.COMPLETED, ImportTaskStatus.FAILED, ImportTaskStatus.CANCELLED):
                    task.completed_at = datetime.now(UTC).isoformat()
            if progress is not None:
                task.progress = progress
            if total is not None:
                task.total = total
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if errors is not None:
                task.errors = errors

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status in (
                ImportTaskStatus.COMPLETED,
                ImportTaskStatus.FAILED,
                ImportTaskStatus.CANCELLED,
            ):
                return False
            task.status = ImportTaskStatus.CANCELLED
            task._cancel_event.set()
            task.completed_at = datetime.now(UTC).isoformat()
            return True

    def is_cancelled(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return True
        return task._cancel_event.is_set() or task.status == ImportTaskStatus.CANCELLED

    def make_progress_callback(self, task_id: str) -> ProgressCallback:
        async def callback(progress: int, total: int, message: str) -> None:
            await self.update_task(
                task_id,
                status=ImportTaskStatus.RUNNING,
                progress=progress,
                total=total,
                message=message,
            )

        return callback
