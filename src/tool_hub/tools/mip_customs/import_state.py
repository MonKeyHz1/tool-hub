"""导入状态持久化 - 基于 SQLite 记录已处理的运单号。

防止重复导入，支持跨次运行的断点续传。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class ImportRecord:
    """导入状态表中的一条记录。"""

    tracking_number: str
    source_file: str
    status: str
    created_at: datetime
    error_message: str | None = None


class ImportState:
    """基于 SQLite 的导入进度追踪器。

    数据库文件默认存储在用户目录下。
    记录每个已成功提交（或已知重复）的运单号，
    后续导入运行时会自动跳过这些记录。
    """

    _TABLE = "imports"

    def __init__(self, db_path: Path | None = None) -> None:
        """初始化导入状态存储。

        Args:
            db_path: 数据库文件路径，默认 ~/.mip_import_state.db。
        """
        self.db_path = db_path or Path.home() / ".mip_import_state.db"
        self._logger = logger.bind(component="ImportState")
        self._init_db()

    def _connection(self) -> sqlite3.Connection:
        """创建数据库连接。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """初始化数据库表结构。"""
        with self._connection() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._TABLE} (
                    tracking_number TEXT PRIMARY KEY,
                    source_file     TEXT NOT NULL,
                    status          TEXT NOT NULL,
                    created_at      TEXT NOT NULL,
                    error_message   TEXT,
                    response_data   TEXT
                )
                """
            )
            # 兼容旧表：添加 response_data 列（如果不存在）
            try:
                conn.execute(
                    f"ALTER TABLE {self._TABLE} ADD COLUMN response_data TEXT"
                )
            except sqlite3.OperationalError:
                pass  # 列已存在
            conn.commit()
        self._logger.debug("db_ready", path=str(self.db_path))

    # ------------------------------------------------------------------
    # 查询方法
    # ------------------------------------------------------------------

    def is_processed(self, tracking_number: str) -> bool:
        """检查运单号是否已处理过。

        Args:
            tracking_number: 运单号。

        Returns:
            已处理返回 True，否则返回 False。
        """
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT 1 FROM {self._TABLE} WHERE tracking_number = ?",
                (tracking_number,),
            ).fetchone()
        return row is not None

    def get_record(self, tracking_number: str) -> ImportRecord | None:
        """查询单个运单号的记录。

        Args:
            tracking_number: 运单号。

        Returns:
            记录对象，不存在则返回 None。
        """
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {self._TABLE} WHERE tracking_number = ?",
                (tracking_number,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self) -> list[ImportRecord]:
        """列出所有记录（按创建时间倒序）。"""
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self._TABLE} ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    # ------------------------------------------------------------------
    # 写入方法
    # ------------------------------------------------------------------

    def mark_processed(
        self,
        tracking_number: str,
        source_file: str,
        status: str = "success",
        error_message: str | None = None,
        response_data: str | None = None,
    ) -> None:
        """标记运单号为已处理（新增或更新）。

        Args:
            tracking_number: 运单号。
            source_file: 来源 Excel 文件路径。
            status: 处理状态（success / duplicate / failed）。
            error_message: 可选的错误信息。
            response_data: 可选的 API 响应 JSON。
        """
        now = datetime.now(UTC).isoformat()
        with self._connection() as conn:
            conn.execute(
                f"""
                INSERT INTO {self._TABLE}
                    (tracking_number, source_file, status, created_at, error_message, response_data)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tracking_number) DO UPDATE SET
                    source_file   = excluded.source_file,
                    status        = excluded.status,
                    created_at    = excluded.created_at,
                    error_message = excluded.error_message,
                    response_data = excluded.response_data
                """,
                (tracking_number, source_file, status, now, error_message, response_data),
            )
            conn.commit()
        self._logger.debug("recorded", tracking_number=tracking_number, status=status)

    def clear(self) -> int:
        """清空所有记录。

        Returns:
            被删除的行数。
        """
        with self._connection() as conn:
            cur = conn.execute(f"DELETE FROM {self._TABLE}")
            conn.commit()
        self._logger.warning("state_cleared", deleted=cur.rowcount)
        return cur.rowcount

    def get_failed(self) -> list[ImportRecord]:
        """获取所有失败（非成功）的记录，用于重试。"""
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self._TABLE} WHERE status != 'success'"
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ImportRecord:
        """将数据库行转换为 ImportRecord 对象。"""
        return ImportRecord(
            tracking_number=row["tracking_number"],
            source_file=row["source_file"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            error_message=row["error_message"],
        )
