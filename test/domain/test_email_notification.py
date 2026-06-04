from datetime import datetime, timedelta, timezone

import pytest

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.common.util.IdGenerator import generate_id
from app.domain.email.EmailNotification import EmailNotification

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_notification(**overrides) -> EmailNotification:
    defaults = dict(
        notification_id=generate_id(),
        recipient="user@example.com",
        subject="Test Subject",
        body="<p>Hello</p>",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
        created_at=_NOW,
        sent_at=None,
    )
    defaults.update(overrides)
    return EmailNotification(**defaults)


class TestEmailNotificationImmutability:
    def test_is_frozen(self):
        n = _make_notification()
        with pytest.raises((AttributeError, TypeError)):
            n.status = NotificationStatus.SENT  # type: ignore[misc]

    def test_mark_sent_returns_new_instance(self):
        n = _make_notification()
        assert n.mark_sent(_NOW) is not n

    def test_mark_failed_returns_new_instance(self):
        n = _make_notification()
        assert n.mark_failed() is not n


class TestMarkSent:
    def test_sets_status_sent(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        assert n.mark_sent(_NOW).status == NotificationStatus.SENT

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


class TestMarkFailed:
    def test_sets_status_failed(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        assert n.mark_failed().status == NotificationStatus.FAILED

    def test_does_not_change_sent_at(self):
        n = _make_notification(sent_at=None)
        assert n.mark_failed().sent_at is None

    def test_does_not_mutate_original(self):
        n = _make_notification(status=NotificationStatus.PENDING)
        n.mark_failed()
        assert n.status == NotificationStatus.PENDING


class TestEmailNotificationFields:
    def test_sent_at_defaults_to_none(self):
        n = _make_notification()
        assert n.sent_at is None

    def test_channel_is_email(self):
        n = _make_notification(channel=NotificationChannel.EMAIL)
        assert n.channel == NotificationChannel.EMAIL

    def test_notification_id_is_24_bytes(self):
        n = _make_notification()
        assert len(n.notification_id) == 24
