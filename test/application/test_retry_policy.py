from datetime import datetime, timezone

from app.application.service.retry.RetryPolicy import RetryPolicy
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.factory.IdFactory import IdFactory

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FakeConfig:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


def _notification(attempts: int) -> EmailNotification:
    return EmailNotification(
        notification_id=IdFactory.generate(),
        recipient=EmailAddress("u@e.com"),
        subject="S",
        body="<p>b</p>",
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.PENDING,
        created_at=_NOW,
        attempts=attempts,
    )


class TestRetryPolicy:
    def test_first_failure_schedules_retry(self):
        policy = RetryPolicy(_FakeConfig())
        result = policy.on_failure(_notification(attempts=0), _NOW, "E084000")
        assert result.status == NotificationStatus.FAILED
        assert result.attempts == 1
        # backoff[0] = 60s
        assert (result.next_retry_at - _NOW).total_seconds() == 60

    def test_backoff_grows_with_attempts(self):
        policy = RetryPolicy(_FakeConfig())
        r2 = policy.on_failure(_notification(attempts=1), _NOW, "E084000")
        assert (r2.next_retry_at - _NOW).total_seconds() == 300  # backoff[1] = 5m

    def test_dead_letter_when_max_reached(self):
        policy = RetryPolicy(_FakeConfig())
        # attempts=4 → attempts_made=5 == default max_attempts → dead-letter
        result = policy.on_failure(_notification(attempts=4), _NOW, "E084000")
        assert result.status == NotificationStatus.DEAD_LETTER
        assert result.attempts == 5

    def test_custom_config(self):
        policy = RetryPolicy(_FakeConfig({
            "notification.retry.max_attempts": 2,
            "notification.retry.backoff_seconds": [10],
        }))
        r1 = policy.on_failure(_notification(attempts=0), _NOW, "E084000")
        assert r1.status == NotificationStatus.FAILED
        assert (r1.next_retry_at - _NOW).total_seconds() == 10
        r2 = policy.on_failure(_notification(attempts=1), _NOW, "E084000")
        assert r2.status == NotificationStatus.DEAD_LETTER
