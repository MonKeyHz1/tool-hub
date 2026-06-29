"""财务系统工具配置。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class FinancialSystemConfig(BaseSettings):
    """财务系统配置。

    配置项通过 FINANCE_ 前缀的环境变量设置。
    """

    model_config = SettingsConfigDict(
        env_prefix="FINANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # TMS 测试环境
    tms_host: str = "https://tms-qa.kimigoshop.com"
    tms_user: str = ""
    tms_password: str = ""

    # 请求超时
    timeout: float = 30.0
