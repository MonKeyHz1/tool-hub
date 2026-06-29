"""MIP API 自定义异常。"""


class MIPAPIError(Exception):
    """MIP API 基础异常。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MIPAuthError(MIPAPIError):
    """认证失败异常。"""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class MIPNotFoundError(MIPAPIError):
    """资源未找到异常。"""

    def __init__(self, message: str = "Item not found") -> None:
        super().__init__(message, status_code=404)


class MIPDuplicateError(MIPAPIError):
    """重复数据异常。"""

    def __init__(self, message: str = "Item already exists") -> None:
        super().__init__(message, status_code=500)


class MIPValidationError(MIPAPIError):
    """参数校验失败异常。"""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, status_code=400)
