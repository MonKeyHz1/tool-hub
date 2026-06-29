"""MIP 海关清关 API 数据模型 - 使用 Pydantic 严格校验。

复用原项目的数据模型设计：
- 所有字段使用 alias 映射到 MIP API 的字段名
- 数量字段序列化为字符串以满足 API 要求
- Y/N 字段做值域校验
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Order(BaseModel):
    """运单信息。"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(..., alias="ORDER_ID", max_length=100)
    mail_bag_number: str | None = Field(default=None, alias="MAIL_BAG_NUMBER", max_length=50)
    net_weight: str | None = Field(default=None, alias="NET_WGT")
    weight: str | None = Field(default=None, alias="WGT")
    weight_unit: str | None = Field(default=None, alias="WGT_UNIT")
    quantity: int | None = Field(default=None, alias="QTY", ge=1)
    quantity_unit: str | None = Field(default=None, alias="QTY_UNIT", max_length=10)

    @field_serializer("quantity")
    def serialize_quantity(self, value: int | None) -> str | None:
        """数量字段序列化为字符串（MIP API 要求）。"""
        if value is None:
            return None
        return str(value)

    length: Decimal | None = Field(default=None, alias="LENGTH")
    width: Decimal | None = Field(default=None, alias="WIDTH")
    height: Decimal | None = Field(default=None, alias="HEIGHT")
    dangerous_goods_code: str | None = Field(default=None, alias="DANG_GOODS_CODE", max_length=20)


class GoodsItem(BaseModel):
    """商品信息（运单中的单件商品）。"""

    model_config = ConfigDict(populate_by_name=True)

    goods_name: str = Field(..., alias="GOODS_NM", max_length=200)
    hs_code: str | None = Field(default=None, alias="HSCODE", max_length=20)
    quantity: int = Field(..., alias="QTY", ge=1)
    quantity_unit: str = Field(..., alias="QTY_UNIT", max_length=10)

    @field_serializer("quantity")
    def serialize_quantity(self, value: int) -> str:
        """数量字段序列化为字符串。"""
        return str(value)

    goods_warning: str | None = Field(default=None, alias="GOODS_WARNING", max_length=200)
    price_1: str = Field(..., alias="PRICE1")
    price_curr_1: str = Field(..., alias="PRICE_CURR1", max_length=3)
    price_2: str | None = Field(default=None, alias="PRICE2")
    price_curr_2: str | None = Field(default=None, alias="PRICE_CURR2", max_length=3)
    price_3: str | None = Field(default=None, alias="PRICE3")
    price_curr_3: str | None = Field(default=None, alias="PRICE_CURR3", max_length=3)
    price_4: str | None = Field(default=None, alias="PRICE4")
    price_curr_4: str | None = Field(default=None, alias="PRICE_CURR4", max_length=3)
    price_5: str | None = Field(default=None, alias="PRICE5")
    price_curr_5: str | None = Field(default=None, alias="PRICE_CURR5", max_length=3)


class Sender(BaseModel):
    """发货人信息。"""

    model_config = ConfigDict(populate_by_name=True)

    country_code: str = Field(..., alias="SHIPPER_CNTRY_CD", max_length=100)
    country_name: str = Field(..., alias="SHIPPER_CNTRY_NM", max_length=100)
    nationality: str | None = Field(default=None, alias="SHIPPER_NATINALITY", max_length=100)
    name_1: str = Field(..., alias="SHIPPER_NM1", max_length=100)
    name_2: str = Field(default="", alias="SHIPPER_NM2", max_length=100)
    registration: str | None = Field(default=None, alias="SHIPPER_REG", max_length=50)
    address: str = Field(..., alias="SHIPPER_ADDR", max_length=200)
    address_1: str | None = Field(default=None, alias="SHIPPER_ADDR1", max_length=200)
    address_2: str | None = Field(default=None, alias="SHIPPER_ADDR2", max_length=200)
    address_3: str | None = Field(default=None, alias="SHIPPER_ADDR3", max_length=200)
    zipcode: str | None = Field(default=None, alias="SHIPPER_ZIPCODE", max_length=20)
    telephone: str | None = Field(default=None, alias="SHIPPER_TEL", max_length=50)


class Receiver(BaseModel):
    """收货人信息。"""

    model_config = ConfigDict(populate_by_name=True)

    country_code: str = Field(..., alias="CONSIGNEE_CNTRY_CD", max_length=2)
    country_name: str = Field(..., alias="CONSIGNEE_CNTRY_NM", max_length=100)
    nationality: str | None = Field(default=None, alias="CONSIGNEE_NATINALITY", max_length=10)
    name_1: str = Field(..., alias="CONSIGNEE_NM1", max_length=100)
    name_2: str = Field(default="", alias="CONSIGNEE_NM2", max_length=100)
    registration: str | None = Field(default=None, alias="CONSIGNEE_REG", max_length=50)
    address: str = Field(..., alias="CONSIGNEE_ADDR", max_length=200)
    address_1: str | None = Field(default=None, alias="CONSIGNEE_ADDR1", max_length=200)
    address_2: str | None = Field(default=None, alias="CONSIGNEE_ADDR2", max_length=200)
    address_3: str | None = Field(default=None, alias="CONSIGNEE_ADDR3", max_length=200)
    zipcode: str | None = Field(default=None, alias="CONSIGNEE_ZIPCODE", max_length=20)
    telephone: str | None = Field(default=None, alias="CONSIGNEE_TEL", max_length=50)
    latitude: Decimal | None = Field(default=None, alias="LATITUDE")
    longitude: Decimal | None = Field(default=None, alias="LONGITUDE")


class Company(BaseModel):
    """运输/物流公司信息。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., alias="COMP_NAME", max_length=200)
    comp_register: str | None = Field(default=None, alias="COMP_REGISTER", max_length=50)
    address: str | None = Field(default=None, alias="COMP_ADDR", max_length=300)
    telephone: str | None = Field(default=None, alias="COMP_TEL", max_length=50)


class CustomsItem(BaseModel):
    """海关清关申报单（一个运单号对应一条）。"""

    model_config = ConfigDict(populate_by_name=True)

    tracking_number: str = Field(..., alias="TRACKING_NUMBER", max_length=50)
    house_seq: str | None = Field(default=None, alias="HOUSE_SEQ", max_length=10)
    mail_id: str = Field(..., alias="MAIL_ID", max_length=50)
    status_id: str | None = Field(default=None, alias="STATUS_ID", max_length=10)
    status_cd: str | None = Field(default=None, alias="STATUS_CD", max_length=50)
    bl_no: str | None = Field(default=None, alias="BL_NO", max_length=50)
    report_type: str | None = Field(default=None, alias="REPORT_TYPE", max_length=20)
    risk_type: str | None = Field(default=None, alias="RISK_TYPE", max_length=5)
    order: Order = Field(..., alias="ORDER")
    goods: list[GoodsItem] = Field(..., alias="GOODS", min_length=1)
    trans_fare: Decimal | None = Field(default=None, alias="TRANS_FARE")
    trans_fare_curr: str | None = Field(default=None, alias="TRANS_FARE_CURR", max_length=3)
    transport_type: str | None = Field(default=None, alias="TRANSPORT_TYPE", max_length=10)
    is_diplomat: str | None = Field(default=None, alias="IS_DIPLOMAT")
    customer_id: str | None = Field(default=None, alias="CUSTOMERID", max_length=20)
    customer_name: str | None = Field(default=None, alias="CUSTOMERNAME", max_length=100)
    sender: Sender = Field(..., alias="SENDER")
    receiver: Receiver = Field(..., alias="RECEIVER")
    company_name: str | None = Field(default=None, alias="COMP_NAME", max_length=200)
    company_register: str | None = Field(default=None, alias="COMP_REGISTER", max_length=50)
    company_addr: str | None = Field(default=None, alias="COMP_ADDR", max_length=300)
    company_tel: str | None = Field(default=None, alias="COMP_TEL", max_length=50)
    reg_date: str | None = Field(default=None, alias="REG_DATE")
    mail_date: str | None = Field(default=None, alias="MAIL_DATE")
    ecommerce_type: str | None = Field(default=None, alias="ECOMMERCE_TYPE")
    ecommerce_link: str | None = Field(default=None, alias="ECOMMERCE_LINK", max_length=500)

    @field_validator("is_diplomat", "ecommerce_type")
    @classmethod
    def validate_yes_no(cls, v: Any) -> Any:
        """校验 Y/N 类型字段。"""
        if v is not None and v not in ("Y", "N"):
            raise ValueError("Must be Y or N")
        return v
