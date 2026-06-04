import grpc
from xime.adapters.grpc.interceptors import configure_grpc_error_mappings
from xime.adapters.grpc.routing import configure_grpc_services

from app.api.grpc.external.NotificationGrpcHandler import NotificationGrpcHandler
from app.api.grpc.generated.notification_pb2_grpc import (
    add_NotificationServiceServicer_to_server,
)
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.OtpAlreadyUsedError import OtpAlreadyUsedError
from app.common.exception.OtpExpiredError import OtpExpiredError
from app.common.exception.OtpNotFoundError import OtpNotFoundError
from app.common.exception.OtpVerificationFailedError import OtpVerificationFailedError

# ── gRPC service registration ─────────────────────────────────────────────────
# Framework đọc registry này khi GrpcAdapter.start() được gọi.

configure_grpc_services(
    packages=["app.api.grpc.external"],
    bindings={
        NotificationGrpcHandler: add_NotificationServiceServicer_to_server,
    },
)

# ── Exception → gRPC StatusCode mapping ──────────────────────────────────────
# ErrorMappingInterceptor tự động map exception sang status code tương ứng.
# Handler không cần try/except.

configure_grpc_error_mappings({
    OtpNotFoundError:           grpc.StatusCode.NOT_FOUND,
    OtpExpiredError:            grpc.StatusCode.FAILED_PRECONDITION,
    OtpAlreadyUsedError:        grpc.StatusCode.FAILED_PRECONDITION,
    OtpVerificationFailedError: grpc.StatusCode.INVALID_ARGUMENT,
    InvalidRecipientError:      grpc.StatusCode.INVALID_ARGUMENT,
})
