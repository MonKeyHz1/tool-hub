"""PDD 商品信息管理 - 存储完整商品字段，支持随机选取生成订单。"""

import json
import random
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...config import settings

DB_PATH = settings.upload_path / "tool_state.db"


def _conn() -> sqlite3.Connection:
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS product_info (
            item_id TEXT PRIMARY KEY,
            item_name TEXT NOT NULL DEFAULT '',
            category_id TEXT NOT NULL DEFAULT '',
            category_name TEXT NOT NULL DEFAULT '',
            total_payment INTEGER NOT NULL DEFAULT 0,
            currency_unit TEXT NOT NULL DEFAULT 'CENT',
            currency TEXT NOT NULL DEFAULT 'CNY',
            item_quantity INTEGER NOT NULL DEFAULT 1,
            pic_url TEXT NOT NULL DEFAULT '',
            sku_property TEXT NOT NULL DEFAULT '',
            goods_type TEXT NOT NULL DEFAULT 'SPECIAL',
            weight REAL NOT NULL DEFAULT 1.0,
            charged_status INTEGER NOT NULL DEFAULT 0,
            magnetic_status INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def add_or_update_product(item: dict) -> None:
    """添加或更新一条商品记录。"""
    conn = _conn()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO product_info
        (item_id, item_name, category_id, category_name, total_payment,
         currency_unit, currency, item_quantity, pic_url, sku_property,
         goods_type, weight, charged_status, magnetic_status, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(item.get("itemId", "")),
            str(item.get("itemName", "")),
            str(item.get("categoryId", "")),
            str(item.get("categoryName", "")),
            int(item.get("totalActualPayment", 0)),
            str(item.get("currencyUnit", "CENT")),
            str(item.get("currency", "CNY")),
            int(item.get("itemQuantity", 1)),
            str(item.get("itemPicUrl", "")),
            str(item.get("itemSkuProperty", "")),
            str(item.get("goodsType", "SPECIAL")),
            float(item.get("weight", 1.0)),
            int(item.get("chargedStatus", 0) or 0),
            int(item.get("magneticStatus", 0) or 0),
            now,
        ),
    )
    conn.commit()
    conn.close()


def get_product(item_id: str) -> dict | None:
    """根据 itemId 获取商品记录。"""
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM product_info WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    cols = ["item_id","item_name","category_id","category_name","total_payment",
            "currency_unit","currency","item_quantity","pic_url","sku_property",
            "goods_type","weight","charged_status","magnetic_status","updated_at"]
    d = dict(zip(cols, row))
    return d


def list_products() -> list[dict]:
    """列出所有商品。"""
    conn = _conn()
    rows = conn.execute("SELECT * FROM product_info ORDER BY item_id").fetchall()
    conn.close()
    cols = ["item_id","item_name","category_id","category_name","total_payment",
            "currency_unit","currency","item_quantity","pic_url","sku_property",
            "goods_type","weight","charged_status","magnetic_status","updated_at"]
    return [dict(zip(cols, r)) for r in rows]


def random_pick_items(count: int = 1) -> list[dict]:
    """从商品表中随机选取 count 个商品，返回 items 数组（用于下单 JSON）。"""
    all_items = list_products()
    if not all_items:
        return []
    picked = random.choices(all_items, k=count)
    result = []
    for p in picked:
        result.append({
            "itemId": p["item_id"],
            "itemName": p["item_name"],
            "categoryId": p["category_id"],
            "categoryName": p["category_name"],
            "totalActualPayment": p["total_payment"],
            "currencyUnit": p["currency_unit"],
            "currency": p["currency"],
            "itemQuantity": p["item_quantity"],
            "itemPicUrl": p["pic_url"],
            "itemSkuProperty": p["sku_property"],
            "goodsType": p["goods_type"],
            "chargedStatus": bool(p["charged_status"]),
            "magneticStatus": bool(p["magnetic_status"]),
        })
    return result


def calculate_order_weight(items: list[dict]) -> float:
    """根据订单 items 计算总重量(kg) = sum(itemWeight * quantity)。"""
    total = 0.0
    for item in items:
        item_id = str(item.get("itemId", ""))
        qty = int(item.get("itemQuantity", 1) or 1)
        prod = get_product(item_id)
        weight = prod["weight"] if prod else 1.0
        total += weight * qty
    return round(total, 2) if total > 0 else 1.0
