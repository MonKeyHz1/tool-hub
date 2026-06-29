"""Temu 网关数据模型。"""

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体。"""

    app_id: str = Field(..., description="Temu 应用 ID")
    app_secret: str = Field(..., description="Temu 应用 Secret（Base64 编码的 AES 密钥）")
    gateway_url: str = Field(default="", description="可选，自定义网关地址")


class LoginResponse(BaseModel):
    """登录响应。"""

    success: bool = Field(..., description="登录是否成功")
    password: str = Field(default="", description="登录返回的 password（用于后续签名）")
    expires_in: int = Field(default=0, description="password 有效期（秒）")
    app_id: str = Field(default="", description="应用 ID")
    message: str = Field(default="", description="提示消息")
    get_auth: dict[str, str] = Field(default_factory=dict, description="GET 请求鉴权头示例")
    post_auth: dict[str, str] = Field(default_factory=dict, description="POST 请求鉴权头示例")


class OrderRequest(BaseModel):
    """下单请求体。"""

    app_id: str = Field(..., description="Temu 应用 ID")
    password: str = Field(..., description="登录返回的 password")
    order_body: dict[str, Any] = Field(default_factory=dict, description="订单 JSON 入参")
    gateway_url: str = Field(default="", description="可选，自定义网关地址")


class ExpressSheetRequest(BaseModel):
    """面单查询请求体。"""

    app_id: str = Field(..., description="Temu 应用 ID")
    password: str = Field(..., description="登录返回的 password")
    reference_no: str = Field(default="", description="订单号（referenceNo）")
    waybill_no: str = Field(default="", description="运单号（waybillNo，尾程面单使用）")
    sheet_type: str = Field(default="express", description="面单类型：express=标准面单, last_mile=尾程面单")
    gateway_url: str = Field(default="", description="可选，自定义网关地址")
