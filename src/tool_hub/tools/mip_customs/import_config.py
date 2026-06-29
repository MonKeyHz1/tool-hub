"""Excel 批量导入的默认值配置。

当 Excel 模板中缺少某些字段时（如发货人信息、价格等），
使用此配置中的默认值填充。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ImportDefaults:
    """Excel 导入时的默认值配置。

    这些值通常在一次批量导入中保持不变，
    例如发货人信息在整个批次中都是相同的。
    """

    # 发货人（Sender）默认信息
    sender_country_code: str = "CN"
    sender_country_name: str = "CHINA"
    sender_nationality: str = "CNN"
    sender_name_1: str = ""
    sender_name_2: str = ""
    sender_registration: str = ""
    sender_address: str = ""
    sender_address_1: str = ""
    sender_address_2: str = ""
    sender_address_3: str = ""
    sender_zipcode: str = ""
    sender_telephone: str = ""

    # 订单默认信息
    order_id_prefix: str = ""

    # 商品价格默认值
    price: Decimal = field(default_factory=lambda: Decimal("0.00"))
    price_currency: str = "RMB"

    # 运输默认信息
    transport_type: str = ""
    trans_fare: Decimal | None = None
    trans_fare_curr: str = ""

    # 其他默认值
    is_diplomat: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    company_name: str | None = None
    company_register: str | None = None
    company_addr: str | None = None
    company_tel: str | None = None
    ecommerce_type: str | None = None
    ecommerce_link: str | None = None

    def generate_order_id(self, tracking_number: str) -> str:
        """根据运单号生成订单 ID。

        Args:
            tracking_number: 运单号。

        Returns:
            生成的订单 ID。
        """
        return f"{self.order_id_prefix}{tracking_number}"
