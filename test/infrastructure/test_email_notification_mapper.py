from datetime import datetime, timedelta, timezone

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.infrastructure.persistence.mapper.EmailNotificationMapper import EmailNotificationMapper

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _domain(**overrides) -> EmailNotification:
    defaults = dict(
        notification_id=IdFactory.generate(),
        recipient=EmailAddress("user@example.com"),
        subject="Hello",
        body="<p>Hi</p>",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.FAILED,
        created_at=_NOW,
        attempts=2,
        next_retry_at=_NOW + timedelta(minutes=5),
        last_error_code="E084000",
        idempotency_key="otp-1",
        caller_service_id="identity-service",
        sent_at=None,
    )
    defaults.update(overrides)
    return EmailNotification(**defaults)


class TestEmailNotificationMapper:
    def test_roundtrip_preserves_fields(self):
        domain = _domain()
        entity = EmailNotificationMapper.to_entity(domain)
        back = EmailNotificationMapper.to_domain(entity)

        assert back.notification_id == domain.notification_id
        assert back.recipient == domain.recipient
        assert back.subject == domain.subject
        assert back.body == domain.body
        assert back.channel == domain.channel
        assert back.status == domain.status
        assert back.attempts == domain.attempts
        assert back.next_retry_at == domain.next_retry_at
        assert back.last_error_code == domain.last_error_code
        assert back.idempotency_key == domain.idempotency_key
        assert back.caller_service_id == domain.caller_service_id

    def test_unknown_caller_stored_as_empty_string(self):
        domain = _domain(caller_service_id=None)
        entity = EmailNotificationMapper.to_entity(domain)
        assert entity.caller_service_id == ""
        # Đọc lại '' → None ở domain.
        assert EmailNotificationMapper.to_domain(entity).caller_service_id is None

    def test_notification_id_stored_as_24_bytes(self):
        entity = EmailNotificationMapper.to_entity(_domain())
        assert len(entity.notification_id) == 24
