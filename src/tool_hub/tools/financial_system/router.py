"""财务系统路由。

提供登录和通用 API 调用接口，支持前端动态新增 API。
每次调用前自动保存请求体 JSON，页面加载时恢复。
"""

import json
from typing import Any

import httpx
import structlog
from fastapi import APIRouter

from ...tool_state import save_state, get_state
from .config import FinancialSystemConfig

logger = structlog.get_logger(component="FinancialSystemAPI")

router = APIRouter(prefix="/api/financial-system", tags=["财务系统"])

TOOL_ID = "financial_system"


@router.post("/login")
async def login(data: dict[str, Any]) -> dict[str, Any]:
    """TMS 测试环境登录，返回 JWT token。

    请求体:
        job_number: 工号
        password: 密码
    """
    config = FinancialSystemConfig()
    job_number = str(data.get("job_number", "")).strip()
    password = str(data.get("password", "")).strip()

    if not job_number or not password:
        return {"success": False, "message": "请输入工号和密码"}

    # 保存登录信息
    save_state(TOOL_ID, {"login_job_number": job_number, "login_password": password})

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}/api/Login/NewLogin",
                json={"jobNumber": job_number, "password": password},
                headers={"Content-Type": "application/json"},
            )
            data_rsp = rsp.json()
            if data_rsp.get("state") and data_rsp.get("data"):
                token = data_rsp["data"]
                # 保存 token
                save_state(TOOL_ID, {"login_token": token})
                return {
                    "success": True,
                    "token": token,
                    "message": f"登录成功, token: {token[:40]}...",
                }
            return {"success": False, "message": f"登录失败: {data_rsp.get('message', rsp.text)}"}
    except Exception as e:
        logger.error("financial_login_error", error=str(e))
        return {"success": False, "message": str(e)}


@router.post("/call")
async def call_api(data: dict[str, Any]) -> dict[str, Any]:
    """调用 TMS API。

    请求体:
        api_key:   接口标识（如 "AddReceivableFinancialStatementDetail"）
        api_path:  API 路径（如 "/FinancialStatement/AddReceivableFinancialStatementDetail"）
        token:     JWT token
        body:      请求体 JSON

    返回 API 响应。
    """
    token = str(data.get("token", "")).strip()
    api_path = str(data.get("api_path", "")).strip()
    api_key = str(data.get("api_key", "")).strip()
    body = data.get("body", {})

    if not token:
        return {"success": False, "message": "请先登录获取 token"}
    if not api_path:
        return {"success": False, "message": "请指定 API 路径"}

    # 保存请求体到状态（按 api_key 索引）
    body_json = json.dumps(body, ensure_ascii=False)
    save_state(TOOL_ID, {f"body_{api_key}": body_json})

    config = FinancialSystemConfig()
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {token}",
    }

    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            rsp = await client.post(
                f"{config.tms_host}{api_path}",
                json=body,
                headers=headers,
            )
            result = rsp.json() if rsp.text else {}
            return {"success": True, "data": result}
    except Exception as e:
        logger.error("financial_call_error", api_path=api_path, error=str(e))
        return {"success": False, "message": str(e)}


@router.get("/saved-body")
async def get_saved_body(api_key: str = "") -> dict[str, Any]:
    """获取指定 API 上次保存的请求体 JSON。

    Query:
        api_key: 接口标识
    """
    if not api_key:
        return {"success": False, "message": "请指定 api_key"}
    state = get_state(TOOL_ID)
    body_json = state.get(f"body_{api_key}", "{}")
    try:
        body = json.loads(body_json)
    except Exception:
        body = {}
    return {"success": True, "data": body}
