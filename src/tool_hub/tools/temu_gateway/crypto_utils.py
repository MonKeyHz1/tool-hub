"""Temu 网关加密工具：AES-128-CBC 登录加密 + HMAC-SHA256 请求签名。"""

import base64
import hashlib
import hmac
import os
import random
import string
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def aes_encrypt(plaintext: str, key_b64: str) -> str:
    """AES-128-CBC 加密，随机 IV 拼接在密文前，Base64 输出。

    Args:
        plaintext: 明文内容。
        key_b64: Base64 编码的 16 字节 AES 密钥。

    Returns:
        Base64 编码的 IV + 密文。
    """
    key = base64.b64decode(key_b64)
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
    return base64.b64encode(iv + ct).decode("utf-8")


def generate_secret(app_id: str, app_secret: str) -> str:
    """生成登录用的 secret: aes_encrypt(random6 + appId + timestamp_秒, appSecret)。

    Args:
        app_id: 应用 ID。
        app_secret: Base64 编码的 AES 密钥。

    Returns:
        加密后的 secret 字符串。
    """
    r = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    ts = str(int(time.time()))
    return aes_encrypt(r + app_id + ts, app_secret)


def generate_sign(body_str: str, password_b64: str, timestamp: str) -> str:
    """HMAC-SHA256 请求签名。

    Args:
        body_str: 请求体 JSON 字符串（GET 请求时传空字符串）。
        password_b64: 登录返回的 password（Base64 编码的 32 字节密钥）。
        timestamp: 秒级时间戳字符串。

    Returns:
        Base64 编码的 HMAC 签名。
    """
    key = base64.b64decode(password_b64)
    msg = (body_str + timestamp).encode("utf-8")
    sig = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b64encode(sig).decode("utf-8")
