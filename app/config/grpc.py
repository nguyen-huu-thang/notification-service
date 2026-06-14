from xime.adapters.grpc import configure_grpc_clients, configure_grpc_services, configure_grpc_tls
from xime.adapters.grpc.interceptors import configure_grpc_interceptors

from clients.trust import KeyDistributionServiceClient
from app.api.grpc.interceptor.AppExceptionInterceptor import AppExceptionInterceptor
from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider
from app.api.grpc.external.NotificationGrpcHandler import NotificationGrpcHandler
from app.api.grpc.generated.notification_pb2_grpc import (
    add_NotificationServiceServicer_to_server,
)

# ── gRPC service registration ─────────────────────────────────────────────────
# Framework đọc registry này khi GrpcAdapter.start() được gọi.

configure_grpc_services(
    packages=["app.api.grpc.external"],
    bindings={
        NotificationGrpcHandler: add_NotificationServiceServicer_to_server,
    },
)

# Dynamic mTLS: certs come from the Trust-synchronized resolvers, re-read on
# every new TLS handshake (rotation without restart). On/off stays in
# application.yml (grpc.tls.enabled).
# mTLS động: cert lấy từ resolver đồng bộ với Trust, đọc lại ở mỗi handshake
# mới (rotate không cần restart). Bật/tắt vẫn nằm ở application.yml.
configure_grpc_tls(provider=TrustGrpcCertificateProvider)

# Platform error standard: this interceptor catches AppException, redacts per the
# GRPC_INTERNAL channel, and aborts with xime-error / xime-error-code metadata.
# It runs innermost (after the framework's built-in interceptors), so it sees the
# handler's exception first and sets the final status.
# Chuẩn mã lỗi platform: interceptor này bắt AppException, che theo kênh
# GRPC_INTERNAL, abort kèm metadata xime-error / xime-error-code. Nó chạy innermost
# (sau interceptor built-in của framework) nên thấy exception của handler trước và
# đặt status cuối cùng.
configure_grpc_interceptors([AppExceptionInterceptor()])

# Outbound gRPC client to Trust. The framework builds a managed XimeGrpcChannel
# from grpc.clients.trust in application.yml (host/port/deadline + dynamic mTLS)
# and registers the SDK client instance in DI so TrustKeyClient can inject it.
# Client gRPC ra Trust. Framework dựng XimeGrpcChannel có quản lý từ
# grpc.clients.trust trong application.yml (host/port/deadline + mTLS động) và
# đăng ký instance client SDK vào DI để TrustKeyClient inject được.
configure_grpc_clients("trust", KeyDistributionServiceClient)
