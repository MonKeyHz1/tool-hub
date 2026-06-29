"""PDD 下单数据模型。"""

from typing import Any

from pydantic import BaseModel, Field


class PDDOrderRequest(BaseModel):
    """PDD 下单请求体。"""

    delivery_type: str = Field(default="homeDelivery", description="配送类型：homeDelivery=上门, selfPickup=自提")
    order_body: dict[str, Any] = Field(default_factory=dict, description="订单 JSON 入参")
