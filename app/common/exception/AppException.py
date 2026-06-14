# Three base exception classes carrying a catalog error code.
# Ba base exception class mang theo một mã lỗi trong catalog.
#
# Throw one of PrivateError / SystemError / PublicError with an errorKey; the
# gRPC interceptor reads `visibility` to redact per channel.
# Ném một trong PrivateError / SystemError / PublicError kèm errorKey; gRPC
# interceptor đọc `visibility` để che lỗi theo kênh.
from app.domain.error.GrpcCode import GrpcCode
from app.domain.error.Visibility import Visibility
from app.domain.error.error_code import get_error


class AppException(Exception):
    def __init__(self, error_key: str, custom_message: str | None = None) -> None:
        d = get_error(error_key)
        self.error_key: str = d.error_key
        self.code: int = d.code
        self.http_status: int = d.http_status
        self.grpc_code: GrpcCode = d.grpc_code
        self.visibility: Visibility = d.visibility
        # custom_message overrides the catalog text and IS what gets serialized,
        # so only pass client-safe text on PUBLIC codes.
        # custom_message ghi đè text catalog và LÀ thứ được serialize, nên chỉ
        # truyền text an toàn cho client trên mã PUBLIC.
        self.message: str = custom_message or d.message
        super().__init__(self.message)


class PrivateError(AppException):
    """visibility = PRIVATE — internal only, redacted on every outbound channel."""


class SystemError(AppException):
    """visibility = SYSTEM — readable by internal services over gRPC mTLS."""


class PublicError(AppException):
    """visibility = PUBLIC — safe for browsers / external REST clients."""
