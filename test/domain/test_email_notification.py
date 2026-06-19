from datetime import datetime, timedelta, timezone

import pytest

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.factory.IdFactory import IdFactory

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_notification(**overrides) -> EmailNotification:
    defaults = dict(
        notification_id=IdFactory.generate(),
        recipient=EmailAddress("user@example.com"),
        subject="Test Subject",
        body="<p>Hello</p>",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
        created_at=_NOW,
        sent_at=None,
    )
    defaults.update(overrides)
    return EmailNotification(**defaults)


class TestEmailNotificationCreate:
    def test_create_generates_24_byte_id(self):
        n = EmailNotification.create(
            recipient=EmailAddress("user@example.com"),
            subject="S",
            body="<p>b</p>",
            now=_NOW,
        )
        assert n.notification_id.is_24_bytes()

    def test_create_starts_pending(self):
        n = EmailNotification.create(
            recipient=EmailAddress("user@example.com"),
            subject="S",
            body="<p>b</p>",
            now=_NOW,
        )
        assert n.status == NotificationStatus.PENDING
        assert n.channel == NotificationChannel.EMAIL
        assert n.sent_at is None


class TestEmailNotificationInvariants:
    def test_empty_subject_raises(self):
        with pytest.raises(ValueError):
            _make_notification(subject="")

    def test_empty_body_raises(self):
        with pytest.raises(ValueError):
            _make_notification(body="")


class TestEmailNotificationImmutability:
    def test_status_is_read_only(self):
        n = _make_notification()
        with pytest.raises(AttributeError):
            n.status = NotificationStatus.SENT  # type: ignore[misc]

    def test_mark_sent_returns_new_instance(self):
        n = _make_notification()
        assert n.mark_sent(_NOW) is not n

    def test_schedule_retry_returns_new_instance(self):
        n = _make_notification()
        assert n.schedule_retry(_NOW, _NOW, "E084000") is not n


class TestMarkSent:
    def test_sets_status_sent(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        sent = n.mark_sent(_NOW)
        assert sent.status == NotificationStatus.SENT
        assert sent.is_sent()

    def test_sets_sent_at(self):
        sent_time = _NOW + timedelta(seconds=1)
        n = _make_notification()
        assert n.mark_sent(sent_time).sent_at == sent_time

    def test_does_not_mutate_original(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        n.mark_sent(_NOW)
        assert n.status == NotificationStatus.PENDING
        assert n.sent_at is None

    def test_preserves_other_fields(self):
        n = _make_notification()
        updated = n.mark_sent(_NOW)
        assert updated.notification_id == n.notification_id
        assert updated.recipient == n.recipient
        assert updated.subject == n.subject
        assert updated.body == n.body


class TestScheduleRetry:
    def test_sets_status_failed_and_retry_fields(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        retry_at = _NOW + timedelta(minutes=5)
        r = n.schedule_retry(_NOW, retry_at, "E084000")
        assert r.status == NotificationStatus.FAILED
        assert r.is_failed()
        assert r.next_retry_at == retry_at
        assert r.last_error_code == "E084000"
        assert r.attempts == n.attempts + 1

    def test_does_not_mutate_original(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        n.schedule_retry(_NOW, _NOW, "E084000")
        assert n.status == NotificationStatus.PENDING
        assert n.attempts == 0


class TestDeadLetter:
    def test_sets_status_dead_letter(self):
        n = _make_notification(status=NotificationStatus.FAILED)
        d = n.dead_letter(_NOW, "E084000")
        assert d.status == NotificationStatus.DEAD_LETTER
        assert d.is_dead_letter()
        assert d.is_terminal()
        assert d.last_error_code == "E084000"
        assert d.next_retry_at is None


class TestEmailNotificationFields:
    def test_sent_at_defaults_to_none(self):
        n = _make_notification()
        assert n.sent_at is None

    def test_channel_is_email(self):
        n = _make_notification(channel=NotificationChannel.EMAIL)
        assert n.channel == NotificationChannel.EMAIL

    def test_notification_id_is_24_bytes(self):
        n = _make_notification()
        assert n.notification_id.length == 24
