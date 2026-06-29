"""工具中心全局配置，从环境变量加载。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """工具中心全局设置。

    所有配置项都可以通过环境变量或 .env 文件设置，
    前缀为 TOOL_HUB_。
    """

    model_config = SettingsConfigDict(
        env_prefix="TOOL_HUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 上传文件存储目录
    upload_dir: str = "./uploads"
    # 最大上传文件大小（字节），默认 50MB
    max_upload_size: int = 52428800
    # 服务监听地址
    host: str = "0.0.0.0"
    # 服务监听端口
    port: int = 8000

    @property
    def upload_path(self) -> Path:
        """返回上传目录的绝对路径，不存在则自动创建。"""
        p = Path(self.upload_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


# 全局配置实例
settings = Settings()
