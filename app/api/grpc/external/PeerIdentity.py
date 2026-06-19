import logging

_log = logging.getLogger(__name__)

# Approach A (service-local) — read the verified client cert CN straight from the
# gRPC ServicerContext. Migrate to request_context.get("caller_service_id") when
# the framework exposes mTLS peer identity centrally.
# Hướng A (service-local) — đọc CN của client cert đã verify ngay từ gRPC context.
# Migrate sang request_context khi framework expose peer identity tập trung.
# Xem: DE-XUAT-CAI-TIEN-FRAMEWORK.md (gốc repo) + .claude/docs/roadmap.md.

_X509_COMMON_NAME = "x509_common_name"


def extract_caller_service_id(context) -> str | None:
    # Fail-soft: trả None nếu không phải mTLS hoặc không có CN — không làm hỏng request.
    try:
        auth = context.auth_context()
    except Exception:
        return None

    if not auth:
        return None

    values = auth.get(_X509_COMMON_NAME) or auth.get(_X509_COMMON_NAME.encode())
    if not values:
        return None

    cn = values[0]
    return cn.decode() if isinstance(cn, (bytes, bytearray)) else str(cn)
