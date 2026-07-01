"""Temu 网关专用 API 路由。

提供三个独立接口：登录、下单、获取面单。
每次请求前自动保存输入到 tool_state，下次打开页面自动恢复。

下单 JSON 支持占位符自动替换（不影响保存的模板）：
  {date} → 当前日期 YYYYMMDD
  {ts}   → 毫秒级时间戳（防止重复）
"""

import base64
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...tool_state import save_state
from ..common_errors import error_response
from .client import TemuGatewayClient
from .crypto_utils import generate_sign
from .models import ExpressSheetRequest, LoginRequest, LoginResponse, OrderRequest

logger = structlog.get_logger(component="TemuGatewayAPI")

router = APIRouter(prefix="/api/temu-gateway", tags=["Temu网关"])

TOOL_ID = "temu_gateway"

# PDF 输出目录（uploads/）
PDF_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "uploads"


@router.post("/login")
async def temu_login(request: LoginRequest) -> dict[str, Any]:
    """Temu 登录鉴权。

    使用 appId + appSecret 调用登录接口，返回 password 用于后续签名。
    请求前自动保存输入值。
    """
    # 保存输入状态
    save_state(TOOL_ID, {
        "login_appId": request.app_id,
        "login_appSecret": request.app_secret,
    })

    try:
        async with TemuGatewayClient(base_url=request.gateway_url) as client:
            result = await client.login(request.app_id, request.app_secret)

        password = result["password"]
        ts = str(int(time.time()))

        # 生成 GET 请求鉴权头示例（body 为空字符串）
        get_sign = generate_sign("", password, ts)
        get_auth = {
            "appId": request.app_id,
            "timestamp": ts,
            "Authorization": get_sign,
        }

        # 生成 POST 请求鉴权头示例（body 为示例 JSON）
        sample_body = '{"orderNumber":"YOUR_ORDER_NO","recipientNation":"KZ"}'
        post_sign = generate_sign(sample_body, password, ts)
        post_auth = {
            "appId": request.app_id,
            "timestamp": ts,
            "Authorization": post_sign,
        }

        # 登录成功后也保存 password 到状态
        save_state(TOOL_ID, {"login_password": password})
        return LoginResponse(
            success=True,
            password=password,
            expires_in=result.get("exp", 0),
            app_id=request.app_id,
            get_auth=get_auth,
            post_auth=post_auth,
        ).model_dump()
    except Exception as e:
        logger.error("temu_login_error", error=str(e))
        return LoginResponse(
            success=False,
            message=str(e),
            error_code=error_response(e).get("error_code", "UNKNOWN_ERROR"),
        ).model_dump()


@router.post("/order")
async def temu_place_order(request: OrderRequest) -> dict[str, Any]:
    """Temu 下单。

    使用登录后的 password 签名，提交订单 JSON 到物流下单接口。
    请求前自动保存输入值（含订单 JSON），下次打开页面自动恢复。
    支持占位符：{date} → 当天日期，{ts} → 毫秒时间戳。
    """
    # 保存输入状态
    order_json_str = json.dumps(request.order_body, ensure_ascii=False)
    save_state(TOOL_ID, {
        "order_appId": request.app_id,
        "order_password": request.password,
        "order_json": order_json_str,
    })

    # 占位符替换（在副本上操作，不修改原始保存的 JSON）
    resolved_body = _resolve_placeholders(request.order_body)

    try:
        async with TemuGatewayClient(base_url=request.gateway_url) as client:
            result = await client.place_order(request.app_id, request.password, resolved_body)

        # 安全提取 API 返回的运单号
        waybill = ""
        try:
            if isinstance(result, dict):
                val = result.get("data")
                if isinstance(val, str):
                    waybill = val
                elif isinstance(val, dict):
                    waybill = val.get("waybillNo") or val.get("waybillNumber") or ""
        except Exception:
            pass

        return {
            "success": True,
            "data": result,
            "sent_order_number": resolved_body.get("orderNumber", ""),
            "sent_recipient_mobile": resolved_body.get("recipientMobile", ""),
            "sent_waybill_no": waybill,
        }
    except Exception as e:
        logger.error("temu_place_order_error", error=str(e))
        return error_response(e)


def _resolve_placeholders(obj: Any) -> Any:
    """递归替换字典/列表/字符串中的占位符。

    支持的占位符：
      {date} → YYYYMMDD
      {ts}   → 毫秒级时间戳（13位，防止重复）

    Args:
        obj: 任意 JSON 可序列化对象。

    Returns:
        替换后的对象副本。
    """
    if isinstance(obj, dict):
        return {k: _resolve_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_placeholders(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        s = s.replace("{date}", datetime.now().strftime("%Y%m%d"))
        s = s.replace("{ts}", str(int(time.time() * 1000)))
        return s
    return obj


@router.post("/express-sheet")
async def temu_express_sheet(request: ExpressSheetRequest) -> dict[str, Any]:
    """查询 Temu 面单。

    根据订单号查询面单，返回的 sheetData 自动解码为 PDF 提供下载。
    请求前自动保存输入值。
    """
    # 保存输入状态
    save_state(TOOL_ID, {
        "express_appId": request.app_id,
        "express_password": request.password,
        "express_referenceNo": request.reference_no,
        "express_waybillNo": request.waybill_no,
        "express_sheetType": request.sheet_type,
    })

    try:
        async with TemuGatewayClient(base_url=request.gateway_url) as client:
            if request.sheet_type == "last_mile":
                result = await client.get_last_mile_sheet(
                    request.app_id, request.password,
                    request.waybill_no, request.reference_no,
                )
            else:
                result = await client.get_express_sheet(
                    request.app_id, request.password, request.reference_no
                )

        # 解码 sheetData 为 PDF
        data = result.get("data") or {} if result else {}
        sheet_data = data.get("sheetData", "")
        pdf_url = None
        if sheet_data:
            PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            pdf_filename = f"temu_label_{request.reference_no}.pdf"
            pdf_path = PDF_OUTPUT_DIR / pdf_filename
            with open(pdf_path, "wb") as f:
                f.write(base64.b64decode(sheet_data))
            pdf_url = f"/api/temu-gateway/download/{pdf_filename}"

        return {
            "success": True,
            "data": result,
            "pdf_url": pdf_url,
        }
    except Exception as e:
        logger.error("temu_express_sheet_error", error=str(e))
        return error_response(e)


@router.get("/download/{filename}")
async def download_pdf(filename: str) -> FileResponse:
    """下载解码后的面单 PDF 文件。"""
    pdf_path = PDF_OUTPUT_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )
