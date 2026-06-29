"""PDD MD5 签名工具。

签约方式：MD5(clientSecret + key1value1key2value2... + clientSecret)
key 按字母序排序，基本类型值转字符串，复杂类型值用 compact JSON。
签名结果放在请求体的 sign 字段中。
"""

import json
import hashlib
from typing import Any


def md5(text: str) -> str:
    """MD5 大写十六进制。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest().upper()


def _is_primitive(value: Any) -> bool:
    """判断是否为基本类型（bool/int/float/str）。"""
    return isinstance(value, (bool, int, float, str))


def sign_pdd(body: dict[str, Any], secret: str) -> str:
    """PDD 旧版 MD5 签名。

    将请求体的所有字段扁平化后按 key 排序拼接，
    前后加上 clientSecret 后计算 MD5。

    Args:
        body: 请求体字典（不含 sign 字段）。
        secret: 客户端密钥。

    Returns:
        32 位大写 MD5 签名。
    """
    params: dict[str, str] = {}
    for k, v in body.items():
        if v is None:
            continue
        if k == "sign":
            continue
        if _is_primitive(v):
            params[k] = str(v)
        else:
            params[k] = json.dumps(v, ensure_ascii=False, separators=(",", ":"))

    sorted_keys = sorted(params.keys())
    sign_src = secret + "".join(f"{k}{params[k]}" for k in sorted_keys) + secret
    return md5(sign_src)
