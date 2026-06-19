# PII-safe helpers for logging. Never log raw recipient addresses.
# Hàm hỗ trợ log an toàn PII. Không bao giờ log địa chỉ người nhận dạng thô.


def mask_email(value: str) -> str:
    # user@example.com -> u***@example.com ; keeps domain for debugging, hides local part.
    # Giữ lại domain để debug, che phần local.
    if not value:
        return "***"

    at = value.find("@")
    if at <= 0:
        return "***"

    return f"{value[0]}***{value[at:]}"
