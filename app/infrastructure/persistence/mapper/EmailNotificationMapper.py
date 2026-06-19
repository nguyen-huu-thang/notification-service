from datetime import timezone

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.model.Id import Id
from app.infrastructure.persistence.entity.EmailNotificationEntity import EmailNotificationEntity


def _aware(dt):
    # Postgres trả naive datetime ở một số driver — ép về UTC-aware.
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class EmailNotificationMapper:

    @staticmethod
    def to_domain(entity: EmailNotificationEntity) -> EmailNotification:
        return EmailNotification(
            notification_id=Id(entity.notification_id),
            recipient=EmailAddress(entity.recipient),
            subject=entity.subject,
            body=entity.body,
            channel=NotificationChannel(entity.channel),
            status=NotificationStatus(entity.status),
            created_at=_aware(entity.created_at),
            attempts=entity.attempts,
            next_retry_at=_aware(entity.next_retry_at),
            last_error_code=entity.last_error_code,
            # Empty string in DB = unknown caller → None in the domain.
            # Chuỗi rỗng trong DB = caller chưa xác định → None ở domain.
            idempotency_key=entity.idempotency_key,
            caller_service_id=entity.caller_service_id or None,
            sent_at=_aware(entity.sent_at),
        )

    @staticmethod
    def to_entity(domain: EmailNotification) -> EmailNotificationEntity:
        entity = EmailNotificationEntity()
        entity.notification_id = domain.notification_id.to_bytes()
        entity.caller_service_id = domain.caller_service_id or ""
        entity.idempotency_key = domain.idempotency_key
        entity.recipient = domain.recipient.value
        entity.subject = domain.subject
        entity.body = domain.body
        entity.channel = domain.channel.value
        entity.status = domain.status.value
        entity.attempts = domain.attempts
        entity.next_retry_at = domain.next_retry_at
        entity.last_error_code = domain.last_error_code
        entity.created_at = domain.created_at
        entity.sent_at = domain.sent_at
        return entity
