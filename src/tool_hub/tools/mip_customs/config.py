"""MIP API 配置，从环境变量加载。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MIPConfig(BaseSettings):
    """MIP 海关清关 API 配置。

    配置项通过 MIP_ 前缀的环境变量或 .env 文件设置。
    """

    model_config = SettingsConfigDict(
        env_prefix="MIP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API 基础地址
    base_url: str = "https://mypost.mn"
    # 访问令牌
    access_token: str = ""
    # 测试环境令牌
    access_token_test: str = ""
    # 生产环境令牌
    access_token_prod: str = ""
    # 请求超时（秒）
    timeout: float = 30.0
    # 环境标识（production / sandbox）
    env: str = "production"
