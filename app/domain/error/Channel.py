# Outgoing channel an error is exposed on — drives redaction (see redaction.py).
# Kênh mà lỗi được phơi bày ra — quyết định việc che lỗi (xem redaction.py).
from enum import Enum


class Channel(Enum):
    # Service-to-service over gRPC mTLS — SYSTEM and PUBLIC may pass through.
    # Liên service qua gRPC mTLS — SYSTEM và PUBLIC được phép lọt.
    GRPC_INTERNAL = 1

    # Browser / external REST — only PUBLIC may pass through.
    # Browser / REST ngoài — chỉ PUBLIC được phép lọt.
    REST_EXTERNAL = 2
