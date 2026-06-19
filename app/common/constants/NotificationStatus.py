from enum import Enum


class NotificationStatus(str, Enum):
    PENDING = "PENDING"          # đã lưu, chưa gửi xong (cửa sổ ngắn giữa save và send)
    SENT = "SENT"                # gửi thành công
    FAILED = "FAILED"            # một lần gửi thất bại, đã lên lịch retry
    DEAD_LETTER = "DEAD_LETTER"  # hết số lần retry, ngừng gửi
