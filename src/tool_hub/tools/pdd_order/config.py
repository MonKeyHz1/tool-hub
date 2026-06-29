"""PDD 集运下单工具配置。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PDDOrderConfig(BaseSettings):
    """PDD 集运下单 API 配置。

    配置项通过 PDD_ 前缀的环境变量或 .env 文件设置。
    """

    model_config = SettingsConfigDict(
        env_prefix="PDD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 网关地址
    gateway_url: str = "https://testwebhook.staritgp.com/pdd-gateway"
    # 客户端密钥（用于 MD5 签名）
    client_secret: str = ""
    # 应用 ID（页面上展示用）
    app_id: str = "KIMIGO_MN"
    # 仓库代码
    warehouse_code: str = "KIMIGO"
    # TMS 测试环境
    tms_host: str = "https://tms-qa.kimigoshop.com"
    tms_user: str = ""
    tms_password: str = ""
    # 数据库（测试库，集包查询用）
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = "kysmallbox"
    # 请求超时（秒）
    timeout: float = 30.0
