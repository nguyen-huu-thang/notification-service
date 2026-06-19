from __future__ import annotations

from datetime import datetime

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.service.retry.RetryPolicy import RetryPolicy
from app.common.exception.AppException import AppException, PublicError
from app.domain.email.model.EmailNotification import EmailNotification


class EmailDeliveryService:
    """Attempts to deliver one notification and returns the updated domain object.

    Gửi một notification và trả về domain object đã cập nhật trạng thái. KHÔNG
    persist (caller tự lưu trong transaction), KHÔNG ném lỗi gửi ra ngoài - mọi
    kết cục gửi được phản ánh vào status để outbox/worker xử lý đồng nhất.

    Dùng chung cho cả request đầu tiên (SendEmailUseCase) lẫn worker retry.
    """

    def __init__(
        self,
        email_sender: EmailSenderPort,
        retry_policy: RetryPolicy,
    ) -> None:
        self._email_sender = email_sender
        self._retry_policy = retry_policy

    async def deliver(
        self,
        notification: EmailNotification,
        now: datetime,
    ) -> EmailNotification:
        try:
            await self._email_sender.send(
                notification.recipient.value,
                notification.subject,
                notification.body,
            )
            return notification.mark_sent(now)
        except PublicError as e:
            # Server từ chối người nhận (mailbox sai...) — lỗi vĩnh viễn, không retry.
            return notification.dead_letter(now, e.error_key)
        except AppException as e:
            # Transient (SystemError) hoặc lỗi cấu hình SMTP (PrivateError) — lên lịch retry.
            return self._retry_policy.on_failure(notification, now, e.error_key)
