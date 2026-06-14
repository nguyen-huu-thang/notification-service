# Error exposure level — drives channel redaction (see redaction.py).
# Mức phơi bày của lỗi — quyết định việc che lỗi theo kênh (xem redaction.py).
from enum import Enum


class Visibility(Enum):
    # Internal to this service only — never leaves, redacted on every channel.
    # Chỉ nội bộ service này — không bao giờ ra ngoài, bị che ở mọi kênh.
    PRIVATE = 1

    # Other services may read it over gRPC mTLS; redacted toward browsers.
    # Service khác đọc được qua gRPC mTLS; bị che khi ra browser.
    SYSTEM = 2

    # Safe for end clients / browsers to read on any channel.
    # An toàn cho client / browser đọc trên mọi kênh.
    PUBLIC = 3
