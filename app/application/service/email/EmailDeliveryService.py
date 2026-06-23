from __future__ import annotations

import logging
import time
from datetime import datetime

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.service.retry.RetryPolicy import RetryPolicy
from app.common.exception.AppException import AppException, PublicError
from app.common.observability import Metrics
from app.common.util.Pii import mask_email
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.sharedkernel.service.IdService import IdService

_log = logging.getLogger(__name__)


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
        notif_id = IdService.to_string(notification.notification_id)
        recipient = mask_email(notification.recipient.value)
        start = time.perf_counter()
        try:
            await self._email_sender.send(
                notification.recipient.value,
                notification.subject,
                notification.body,
            )
        except PublicError as e:
            # Server từ chối người nhận (mailbox sai...) — lỗi vĩnh viễn, không retry.
            Metrics.EMAILS_FAILED.labels(reason="rejected").inc()
            Metrics.EMAILS_DEAD_LETTER.inc()
            _log.warning(
                "email_dead_letter",
                extra={
                    "event": "email_dead_letter",
                    "notification_id": notif_id,
                    "recipient": recipient,
                    "error_code": e.error_key,
                    "attempts": notification.attempts,
                },
            )
            return notification.dead_letter(now, e.error_key)
        except AppException as e:
            # Transient (SystemError) hoặc lỗi cấu hình SMTP (PrivateError) — lên lịch retry.
            Metrics.EMAILS_FAILED.labels(reason="transient").inc()
            _log.warning(
                "email_send_failed",
                extra={
                    "event": "email_send_failed",
                    "notification_id": notif_id,
                    "recipient": recipient,
                    "error_code": e.error_key,
                    "attempts": notification.attempts,
                },
            )
            return self._retry_policy.on_failure(notification, now, e.error_key)
        else:
            Metrics.EMAILS_SENT.inc()
            _log.info(
                "email_sent",
                extra={
                    "event": "email_sent",
                    "notification_id": notif_id,
                    "recipient": recipient,
                    "attempts": notification.attempts,
                },
            )
            return notification.mark_sent(now)
        finally:
            Metrics.SEND_DURATION.observe(time.perf_counter() - start)
