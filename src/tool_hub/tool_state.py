"""公共持久化存储模块 - 基于 SQLite 为每个工具保存/恢复上次使用的表单数据。

每个工具的 key-value 数据存储在 uploads/tool_state.db 中，
前端通过 GET /api/tool-state/{tool_id} 获取，后端自动保存。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from .config import settings

logger = structlog.get_logger(component="ToolState")

DB_PATH = settings.upload_path / "tool_state.db"


def _conn() -> sqlite3.Connection:
    """获取数据库连接，自动创建表。"""
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_state (
            tool_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tool_id, key)
        )"""
    )
    conn.commit()
    return conn


def get_state(tool_id: str) -> dict[str, Any]:
    """读取工具的持久化状态。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT key, value FROM tool_state WHERE tool_id = ?", (tool_id,)
    ).fetchall()
    conn.close()
    result: dict[str, Any] = {}
    for k, v in rows:
        try:
            result[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            result[k] = v
    logger.info("tool_state_loaded", tool_id=tool_id, keys=len(result))
    return result


def save_state(tool_id: str, data: dict[str, Any]) -> None:
    """保存工具的输入数据（合并已有数据，新值覆盖旧值）。"""
    existing = get_state(tool_id)
    existing.update({k: v for k, v in data.items() if v not in (None, "", [])})
    now = datetime.now(UTC).isoformat()
    conn = _conn()
    for k, v in existing.items():
        conn.execute(
            "INSERT OR REPLACE INTO tool_state (tool_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
            (tool_id, k, json.dumps(v, ensure_ascii=False), now),
        )
    conn.commit()
    conn.close()
    logger.info("tool_state_saved", tool_id=tool_id, keys=len(existing))
