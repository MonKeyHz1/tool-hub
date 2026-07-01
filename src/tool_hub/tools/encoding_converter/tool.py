"""编码转换工具 - 按源编码读取文件，转换为目标编码后输出。"""

from __future__ import annotations

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
    """文件编码转换工具。

    上传文件 → 选择/检测源编码 → 按目标编码重新编码 → 下载转换后的文件。
    """

    tool_id = "encoding_converter"
    tool_name = "编码转换"
    tool_description = "按源编码读取文件并转换为目标编码（UTF-8/GBK/BIG5 等），支持下载转换后的文件"

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
                    "source_encoding": {
                        "type": "string",
                        "enum": ["auto"] + self.ENCODINGS,
                        "default": "auto",
                        "description": "源编码格式，选择 auto 将自动检测",
                    },
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
        request_host: str = "",
    ) -> ToolResult:
        """执行编码转换。

        Args:
            params: 包含 source_encoding / target_encoding 参数。
            file_path: 上传的文件路径。
            request_host: 请求 Host（用于生成下载链接）。

        Returns:
            ToolResult 包含检测到的编码、转换结果和下载链接。
        """
        if file_path is None:
            return ToolResult(success=False, message="请先上传文件")

        if not file_path.exists():
            return ToolResult(success=False, message=f"文件不存在: {file_path}")

        source_encoding = params.get("source_encoding", "auto").strip().lower()
        target_encoding = params.get("target_encoding", "utf-8").strip().lower()
        started_at = datetime.now(UTC).isoformat()

        try:
            # 读取原始文件
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            file_size = len(raw_bytes)
            file_name = file_path.stem + file_path.suffix

            # 二进制文件直接拒绝（如 xlsx/docx/pdf 等）
            if file_size > 0 and b"\x00" in raw_bytes[:4096]:
                return ToolResult(
                    success=False,
                    message="检测到二进制文件，暂不支持转换。请上传文本类文件（如 .txt/.csv/.json）",
                    errors=[{"error_type": "BINARY_FILE", "message": "二进制文件不支持编码转换"}],
                )

            # 确定源编码
            detected_encoding = "unknown"
            confidence = 0.0
            if source_encoding == "auto":
                detected = chardet.detect(raw_bytes)
                detected_encoding = detected.get("encoding") or "unknown"
                confidence = detected.get("confidence", 0)
                if detected_encoding and detected_encoding.lower() != "unknown":
                    source_encoding = detected_encoding.lower()
                else:
                    source_encoding = "utf-8"
                    confidence = 0.0
            else:
                detected_encoding = source_encoding

            logger.info(
                "encoding_convert_start",
                file_name=file_name,
                source_encoding=source_encoding,
                detected_encoding=detected_encoding,
                confidence=round(confidence * 100, 1),
                target_encoding=target_encoding,
            )

            # 按源编码解码
            try:
                text = raw_bytes.decode(source_encoding)
            except UnicodeDecodeError as exc:
                logger.warning(
                    "encoding_decode_failed",
                    source_encoding=source_encoding,
                    error=str(exc),
                )
                return ToolResult(
                    success=False,
                    message=f"无法用 {source_encoding} 解码文件，请尝试手动选择源编码",
                    errors=[{"error_type": "DECODE_ERROR", "message": str(exc), "source_encoding": source_encoding}],
                )

            # 按目标编码重新编码
            converted_bytes = text.encode(target_encoding)

            # 保存转换后的文件（原文件名 + _new）
            output_name = f"{file_path.stem}_new{file_path.suffix}"
            output_path = file_path.parent / output_name
            with open(output_path, "wb") as f:
                f.write(converted_bytes)

            # 根据请求 Host 生成下载链接，避免 localhost 硬编码
            host = request_host or f"localhost:{settings.port}"
            scheme = "https" if host.endswith((":443", ".443")) else "http"
            download_url = f"{scheme}://{host}/files/{output_name}"

            message = f"转换完成: {source_encoding} → {target_encoding}"
            if source_encoding != detected_encoding.lower():
                message = f"转换完成: 检测为 {detected_encoding}({round(confidence * 100, 1)}%)，按 {source_encoding} → {target_encoding} 输出"

            return ToolResult(
                success=True,
                message=message,
                data={
                    "file_name": file_name,
                    "file_size": file_size,
                    "source_encoding": source_encoding,
                    "detected_encoding": detected_encoding,
                    "detection_confidence": round(confidence * 100, 1),
                    "target_encoding": target_encoding,
                    "converted_size": len(converted_bytes),
                    "download_url": download_url,
                },
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.exception("encoding_converter_error", error=str(e))
            return ToolResult(
                success=False,
                message=f"转换失败: {e}",
                errors=[{"error_type": "CONVERSION_ERROR", "message": str(e)}],
            )
