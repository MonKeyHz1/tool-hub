"""编码转换工具专用 API 路由。

提供 Base64 转 PDF 等辅助接口。
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...config import settings
from ..common_errors import error_response

logger = structlog.get_logger()

router = APIRouter(prefix="/encoding-converter", tags=["encoding-converter"])


@router.post("/base64-to-pdf")
async def base64_to_pdf(data: dict[str, Any]) -> dict[str, Any]:
    """将 Base64 文本解码并保存为 PDF 文件，返回下载链接。"""
    base64_text = data.get("base64", "")
    if not base64_text:
        return {"success": False, "message": "Base64 内容不能为空"}

    try:
        pdf_bytes = base64.b64decode(base64_text)
    except Exception as e:
        logger.error("base64_decode_failed", error=str(e))
        return {"success": False, "message": f"Base64 解码失败: {e}"}

    if len(pdf_bytes) < 10:
        return {"success": False, "message": "解码后数据太短，可能不是有效的 PDF"}

    if not pdf_bytes.startswith(b"%PDF"):
        return {"success": False, "message": "解码后不是有效的 PDF 文件"}

    try:
        output_dir = settings.upload_path
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"base64_{uuid.uuid4().hex[:12]}.pdf"
        output_path = output_dir / filename
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        return {
            "success": True,
            "message": "PDF 生成成功",
            "data": {
                "filename": filename,
                "size": len(pdf_bytes),
                "download_url": f"/api/encoding-converter/download/{filename}",
                "created_at": datetime.now(UTC).isoformat(),
            },
        }
    except Exception as e:
        logger.exception("base64_to_pdf_failed", error=str(e))
        return error_response(e)


@router.get("/download/{filename}")
async def download_pdf(filename: str) -> FileResponse:
    """下载 Base64 解码生成的 PDF 文件。"""
    pdf_path = settings.upload_path / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )
