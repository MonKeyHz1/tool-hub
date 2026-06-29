"""编码转换工具 - 检测文件编码并转换为目标编码。"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chardet
import structlog

from ...config import settings
from ...models import ToolMeta, ToolResult
from ..base import BaseTool

logger = structlog.get_logger()


class EncodingConverterTool(BaseTool):
    """文件编码检测与转换工具。

    上传文件 → 检测当前编码 → 转换为目标编码 → 下载转换后的文件。
    """

    tool_id = "encoding_converter"
    tool_name = "编码转换"
    tool_description = "检测文件编码并转换为目标编码（UTF-8/GBK/BIG5 等），支持下载转换后的文件"

    # 常用编码列表
    ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "shift_jis", "euc_jp", "latin-1", "utf-16", "ascii"]

    def get_meta(self) -> ToolMeta:
        return ToolMeta(
            tool_id=self.tool_id,
            tool_name=self.tool_name,
            description=self.tool_description,
            version="0.1.0",
            requires_file=True,
            accepted_file_types=[".txt", ".csv", ".json", ".xml", ".html", ".sql", ".md", ".py", ".js", ".ts", ".log", "*"],
            input_schema={
                "type": "object",
                "properties": {
                    "target_encoding": {
                        "type": "string",
                        "enum": self.ENCODINGS,
                        "default": "utf-8",
                        "description": "目标编码格式",
                    },
                },
            },
        )

    async def execute(
        self,
        params: dict[str, Any],
        file_path: Path | None = None,
    ) -> ToolResult:
        """执行编码转换。

        Args:
            params: 包含 target_encoding 参数。
            file_path: 上传的文件路径。

        Returns:
            ToolResult 包含检测到的编码、转换结果和下载链接。
        """
        if file_path is None:
            return ToolResult(success=False, message="请先上传文件")

        if not file_path.exists():
            return ToolResult(success=False, message=f"文件不存在: {file_path}")

        target_encoding = params.get("target_encoding", "utf-8")
        started_at = datetime.now(UTC).isoformat()

        try:
            # 读取原始文件
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            file_size = len(raw_bytes)
            file_name = file_path.stem + file_path.suffix

            # 检测编码
            detected = chardet.detect(raw_bytes)
            detected_encoding = detected.get("encoding") or "unknown"
            confidence = detected.get("confidence", 0)

            # 转换编码
            if detected_encoding and detected_encoding.lower() != "unknown":
                text = raw_bytes.decode(detected_encoding)
            else:
                # 兜底：尝试 UTF-8
                text = raw_bytes.decode("utf-8")

            converted_bytes = text.encode(target_encoding)

            # 保存转换后的文件（原文件名 + _new）
            output_name = f"{file_path.stem}_new{file_path.suffix}"
            output_path = file_path.parent / output_name
            with open(output_path, "wb") as f:
                f.write(converted_bytes)

            download_url = f"http://localhost:8000/files/{output_name}"

            return ToolResult(
                success=True,
                message=f"转换完成: {detected_encoding} → {target_encoding}",
                data={
                    "file_name": file_name,
                    "file_size": file_size,
                    "detected_encoding": detected_encoding,
                    "detection_confidence": round(confidence * 100, 1),
                    "target_encoding": target_encoding,
                    "converted_size": len(converted_bytes),
                    "download_url": download_url,
                },
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
            )

        except UnicodeDecodeError as e:
            return ToolResult(
                success=False,
                message=f"编码解码失败: {e}",
                errors=[{"error_type": "DECODE_ERROR", "message": str(e)}],
            )
        except Exception as e:
            logger.exception("encoding_converter_error", error=str(e))
            return ToolResult(
                success=False,
                message=f"转换失败: {e}",
                errors=[{"error_type": "CONVERSION_ERROR", "message": str(e)}],
            )
