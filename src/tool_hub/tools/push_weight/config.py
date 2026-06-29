"""推送重量工具配置。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PushWeightConfig(BaseSettings):
    """推送重量工具配置。

    配置项通过 PUSH_WEIGHT_ 前缀的环境变量设置。
    """

    model_config = SettingsConfigDict(
        env_prefix="PUSH_WEIGHT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # TMS 生产环境
    tms_host: str = "https://tms.prod.kimigoshop.com"
    tms_user: str = ""
    tms_password: str = ""

    # 生产库（只读查询）
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = "kysmallbox"

    # 推送间隔（秒）
    push_interval: float = 1.0

    # 请求超时
    timeout: float = 30.0
