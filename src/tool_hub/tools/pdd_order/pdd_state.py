"""PDD 订单状态持久化 - 基于 SQLite 记录每笔订单的流程状态。"""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...config import settings

DB_PATH = settings.upload_path / "tool_state.db"


def _conn() -> sqlite3.Connection:
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS pdd_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL DEFAULT '',
            delivery_type TEXT NOT NULL,
            logistics_order_code TEXT NOT NULL,
            mail_no TEXT NOT NULL,
            pp_code TEXT NOT NULL,
            order_code TEXT NOT NULL,
            buyer_code TEXT NOT NULL DEFAULT '',
            trade_sn TEXT NOT NULL DEFAULT '',
            status_inbound TEXT DEFAULT '',
            status_weigh TEXT DEFAULT '',
            status_shelf TEXT DEFAULT '',
            status_unpack TEXT DEFAULT '',
            status_outbound TEXT DEFAULT '',
            status_bag TEXT DEFAULT '',
            status_vehicle TEXT DEFAULT '',
            status_dispatch TEXT DEFAULT '',
            error_msg TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def save_order(**kwargs: Any) -> int:
    """保存一条下单记录，返回自增ID。"""
    conn = _conn()
    now = datetime.now(UTC).isoformat()
    cur = conn.execute(
        """INSERT INTO pdd_orders (batch_id, delivery_type, logistics_order_code, mail_no,
           pp_code, order_code, buyer_code, trade_sn, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            kwargs.get("batch_id", ""),
            kwargs.get("delivery_type", ""),
            kwargs.get("logistics_order_code", ""),
            kwargs.get("mail_no", ""),
            kwargs.get("pp_code", ""),
            kwargs.get("order_code", ""),
            kwargs.get("buyer_code", ""),
            kwargs.get("trade_sn", ""),
            now,
            now,
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def update_order_status(tracking: str, step: str, status: str, error_msg: str = "") -> None:
    """根据运单号或order_code更新订单某步状态。"""
    conn = _conn()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        f"UPDATE pdd_orders SET status_{step} = ?, error_msg = ?, updated_at = ? WHERE mail_no = ? OR order_code = ?",
        (status, error_msg, now, tracking, tracking),
    )
    conn.commit()
    conn.close()


def get_order(order_code: str) -> dict | None:
    """根据 order_code 查询一条订单。"""
    conn = _conn()
    row = conn.execute("SELECT * FROM pdd_orders WHERE order_code = ?", (order_code,)).fetchone()
    conn.close()
    if not row:
        return None
    cols = [d[0] for d in conn.execute("PRAGMA table_info(pdd_orders)").fetchall()]
    return dict(zip(cols, row)) if hasattr(conn, 'close') else None
