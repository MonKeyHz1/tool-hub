"""推送重量路由。

提供查询和推送两个接口：
- POST /api/push-weight/query  — 查库（只读，获取尾程单号 + 出库通知状态）
- POST /api/push-weight/push   — 推送重量到 TMS 生产
"""

from typing import Any

import httpx
import pymysql
import structlog
from fastapi import APIRouter
from pymysql.cursors import DictCursor

from ...tool_state import save_state
from ..common_errors import error_response
from .config import PushWeightConfig

logger = structlog.get_logger(component="PushWeightAPI")

router = APIRouter(prefix="/api/push-weight", tags=["推送重量"])

TOOL_ID = "push_weight"


def _get_db_conn(config: PushWeightConfig):
    """获取生产库只读连接。"""
    conn = pymysql.connect(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )
    # 只读隔离级别，避免锁
    with conn.cursor() as c:
        c.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return conn


@router.post("/query")
async def query_numbers(data: dict[str, Any]) -> dict[str, Any]:
    """查询快递单号对应的尾程单号和出库通知状态。

    请求体:
        numbers: 快递单号列表 (list[str])

    返回:
        每条数据包含: tracking_number, order_number, ky_in_storage_number,
        reality_cross_weight, has_outbound_notice
    """
    numbers = data.get("numbers", [])
    if not numbers or not isinstance(numbers, list):
        return {"success": False, "message": "请提供快递单号列表"}

    # 去重
    numbers = list(set(str(n).strip() for n in numbers if str(n).strip()))
    if not numbers:
        return {"success": False, "message": "无有效单号"}

    # 保存输入
    input_text = "\n".join(numbers)
    save_state(TOOL_ID, {"last_input": input_text})

    config = PushWeightConfig()
    if not config.db_host:
        return {"success": False, "message": "数据库未配置，请检查 .env"}

    try:
        conn = _get_db_conn(config)
        cursor = conn.cursor()
    except Exception as e:
        return {**error_response(e), "message": f"数据库连接失败: {e}"}

    try:
        # 1. 查询 customer_order 获取尾程单号（优先按 tracking_number 查）
        placeholders = ",".join(["%s"] * len(numbers))
        sql_co = (
            f"SELECT order_number, tracking_number, ky_in_storage_number, reality_cross_weight "
            f"FROM customer_order WHERE tracking_number IN ({placeholders})"
        )
        cursor.execute(sql_co, numbers)
        co_rows = {r["tracking_number"]: r for r in cursor.fetchall()}

        # 2. 查询 outbound_notice_mail_detail 检查出库通知是否存在
        sql_ob = (
            f"SELECT mail_no FROM outbound_notice_mail_detail "
            f"WHERE mail_no IN ({placeholders})"
        )
        cursor.execute(sql_ob, numbers)
        ob_set = {r["mail_no"] for r in cursor.fetchall()}

        # 3. 组装结果
        results = []
        for num in numbers:
            co = co_rows.get(num)
            has_ob = num in ob_set
            results.append({
                "tracking_number": num,
                "order_number": co["order_number"] if co else None,
                "ky_in_storage_number": co["ky_in_storage_number"] if co else None,
                "reality_cross_weight": co["reality_cross_weight"] if co else None,
                "has_outbound_notice": has_ob,
                "found_in_db": co is not None,
            })

        found_count = sum(1 for r in results if r["found_in_db"])
        missing = [r["tracking_number"] for r in results if not r["found_in_db"]]

        return {
            "success": True,
            "data": results,
            "total": len(results),
            "found_in_db": found_count,
            "not_found_in_db": len(missing),
            "missing_numbers": missing,
        }
    except Exception as e:
        logger.error("push_weight_query_error", error=str(e))
        return error_response(e)
    finally:
        cursor.close()
        conn.close()


@router.post("/push")
async def push_numbers(data: dict[str, Any]) -> dict[str, Any]:
    """推送重量到 TMS 生产环境。

    请求体:
        numbers: 尾程单号列表 (list[str])
        force: 是否跳过确认 (bool, 前端已做确认，后端此处保留)

    注意: 此操作直接调用生产 TMS 接口，请谨慎使用。
    """
    numbers = data.get("numbers", [])
    if not numbers or not isinstance(numbers, list):
        return {"success": False, "message": "请提供尾程单号列表"}

    numbers = [str(n).strip() for n in numbers if str(n).strip()]
    if not numbers:
        return {"success": False, "message": "无有效单号"}

    config = PushWeightConfig()
    logger.info("push_weight_push_start", total=len(numbers), tms_host=config.tms_host, tms_user=config.tms_user)
    if not config.tms_host or not config.tms_user:
        logger.error("push_weight_config_missing")
        return {"success": False, "message": "TMS 未配置，请检查 .env"}

    # 登录 TMS
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            login_url = f"{config.tms_host}/api/Login/NewLogin"
            logger.info("push_weight_tms_login_request", url=login_url, job_number=config.tms_user)
            login_rsp = await client.post(
                login_url,
                json={"jobNumber": config.tms_user, "password": config.tms_password},
                headers={"Content-Type": "application/json"},
            )
            logger.info("push_weight_tms_login_response", status_code=login_rsp.status_code, text=login_rsp.text[:500])
            login_data = login_rsp.json()
            if not login_data.get("state") or not login_data.get("data"):
                logger.error("push_weight_tms_login_failed", response=login_data)
                return {"success": False, "message": f"TMS 登录失败: {login_data}"}
            token = login_data["data"]
            logger.info("push_weight_tms_login_success", token_prefix=token[:20])

            headers = {"Authorization": f"Bearer {token}"}
            success_list = []
            failed_list = []

            for i, num in enumerate(numbers):
                push_url = f"{config.tms_host}/demo/pushPddOrderCrossLine"
                logger.info("push_weight_push_one", index=i + 1, total=len(numbers), number=num, url=push_url)
                try:
                    rsp = await client.get(
                        push_url,
                        params={"kyInstoreNumber": num},
                        headers=headers,
                    )
                    body_text = rsp.text
                    body = rsp.json() if body_text else {}
                    code = body.get("code") if isinstance(body, dict) else None
                    logger.info(
                        "push_weight_push_one_response",
                        index=i + 1,
                        number=num,
                        status_code=rsp.status_code,
                        code=code,
                        state=body.get("state") if isinstance(body, dict) else None,
                        body=str(body)[:500],
                    )

                    if code in (200, 0) or body.get("state"):
                        success_list.append({"number": num, "result": body})
                        logger.info("push_weight_push_one_success", index=i + 1, number=num)
                    else:
                        failed_list.append({"number": num, "result": body})
                        logger.warning("push_weight_push_one_failed", index=i + 1, number=num, result=body)
                except Exception as e:
                    err = error_response(e)
                    logger.error("push_weight_push_one_error", index=i + 1, number=num, error_code=err.get("error_code"), error=err.get("message"))
                    failed_list.append({"number": num, "error": err.get("message", str(e)), "error_code": err.get("error_code")})

                # 间隔
                if i < len(numbers) - 1:
                    import asyncio
                    await asyncio.sleep(config.push_interval)

        logger.info(
            "push_weight_push_complete",
            total=len(numbers),
            success_count=len(success_list),
            failed_count=len(failed_list),
        )
        return {
            "success": len(failed_list) == 0,
            "total": len(numbers),
            "success_count": len(success_list),
            "failed_count": len(failed_list),
            "success_list": success_list,
            "failed_list": failed_list,
        }
    except Exception as e:
        logger.error("push_weight_push_error", error=str(e))
        return error_response(e)
