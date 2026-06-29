"""通用数据模型，用于工具执行的标准化输入输出。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolMeta(BaseModel):
    """工具的元信息，用于前端展示工具列表。"""

    tool_id: str = Field(..., description="工具唯一标识")
    tool_name: str = Field(..., description="工具显示名称")
    description: str = Field(default="", description="工具功能描述")
    version: str = Field(default="0.1.0", description="工具版本")
    # 是否需要上传文件
    requires_file: bool = Field(default=False, description="是否需要上传文件")
    # 支持的文件类型（如 .xlsx, .xls）
    accepted_file_types: list[str] = Field(default_factory=list, description="支持的文件类型")
    # 工具的配置参数定义（JSON Schema 格式）
    input_schema: dict[str, Any] = Field(default_factory=dict, description="输入参数 JSON Schema")
    # 是否隐藏（不在主页列表展示，供子 Tab 使用）
    hidden: bool = Field(default=False, description="是否在主页隐藏")


class ExecuteRequest(BaseModel):
    """前端发起工具执行的请求体。"""

    tool_id: str = Field(..., description="要执行的工具ID")
    # 工具执行参数（键值对，根据各工具的 input_schema 填入）
    params: dict[str, Any] = Field(default_factory=dict, description="执行参数")
    # 上传文件的 ID（上传接口返回）
    file_id: str | None = Field(default=None, description="关联的文件ID")


class ToolResult(BaseModel):
    """工具执行的返回结果。"""

    success: bool = Field(..., description="执行是否成功")
    message: str = Field(default="", description="结果摘要消息")
    data: Any = Field(default=None, description="执行结果数据")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="错误详情列表")
    started_at: str | None = Field(default=None, description="开始时间 (ISO 格式)")
    completed_at: str | None = Field(default=None, description="完成时间 (ISO 格式)")


class FileUploadResult(BaseModel):
    """文件上传的返回结果。"""

    file_id: str = Field(..., description="文件唯一标识")
    original_name: str = Field(..., description="原始文件名")
    size: int = Field(..., description="文件大小（字节）")
    stored_path: str = Field(..., description="服务端存储路径")
    uploaded_at: str = Field(..., description="上传时间 (ISO 格式)")
