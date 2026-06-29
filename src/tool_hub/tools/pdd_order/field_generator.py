"""PDD 下单动态字段生成器。

根据数据库规则 + 时间戳自动生成唯一字段值。
"""

import hashlib
import random
import string
import time
from datetime import datetime


def _yyMMdd() -> str:
    return datetime.now().strftime("%y%m%d")


def _ts_ms() -> str:
    return str(int(time.time() * 1000))


def _rand_digits(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))


def _rand_upper(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase, k=n))


def gen_logistics_order_code() -> str:
    """生成物流订单号: PC + YYMMDD + 13位毫秒时间戳 + 6位随机数字。"""
    return f"PC{_yyMMdd()}{_ts_ms()}{_rand_digits(6)}"


def gen_buyer_code() -> str:
    """生成买家编码: 32位 MD5 十六进制。"""
    seed = f"{time.time_ns()}{random.getrandbits(128)}"
    return hashlib.md5(seed.encode()).hexdigest()


def gen_dere_recog_code() -> str:
    """生成识别码: @DD#{5位数字}{2位大写}{1位大写}{6位数字}#。"""
    return f"@DD#{_rand_digits(5)}{_rand_upper(2)}{_rand_upper(1)}{_rand_digits(6)}#"


def gen_mail_no(express_code: str = "SF") -> str:
    """生成运单号: express_code + 13位毫秒时间戳 + 4位随机数字。"""
    return f"{express_code}{_ts_ms()}{_rand_digits(4)}"


def gen_trade_order_sn() -> str:
    """生成交易订单号: YYMMDD-13位毫秒时间戳 + 2位随机数字。"""
    return f"{_yyMMdd()}-{_ts_ms()}{_rand_digits(2)}"


def generate_dynamic_fields(body: dict) -> dict:
    """为请求体自动生成所有动态字段。

    Args:
        body: 请求体模板（会被复制，原对象不修改）。

    Returns:
        填充了动态字段的新字典。
    """
    import json as _json

    result = _json.loads(_json.dumps(body))  # 深拷贝

    result["logisticsOrderCode"] = gen_logistics_order_code()
    result["buyerCode"] = gen_buyer_code()
    result["dereRecogCode"] = gen_dere_recog_code()

    # 生成 paymentDetail
    result["paymentDetail"] = {
        **(result.get("paymentDetail") or {}),
        "tradeOrderSn": gen_trade_order_sn(),
    }

    # 生成 mailDetails
    mail_details = result.get("mailDetails", [])
    for md in mail_details:
        ec = md.get("expressCode", "SF")
        md["mailNo"] = gen_mail_no(ec)

    return result
