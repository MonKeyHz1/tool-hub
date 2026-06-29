"""Temu Gateway 配置，从环境变量加载。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class TemuGatewayConfig(BaseSettings):
    """Temu 网关 API 配置。

    配置项通过 TEMU_ 前缀的环境变量或 .env 文件设置。
    """

    model_config = SettingsConfigDict(
        env_prefix="TEMU_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 网关地址
    gateway_url: str = "https://testwebhook.staritgp.com/gateway"
    # 可替换地址
    gateway_urls: str = ""  # 逗号分隔的额外地址列表，前端可选择
    # 请求超时（秒）
    timeout: float = 30.0
