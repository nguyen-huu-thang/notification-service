from xime.adapters.grpc.routing import configure_grpc_services

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
