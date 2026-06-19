from datetime import datetime, timezone

import pytest

from app.application.service.email.NotificationCleanupService import NotificationCleanupService


class _FakeConfig:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


class _FakeTx:
    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeDeleteRepo:
    def __init__(self):
        self.called_with = None

    async def delete_old(self, sent_before, dead_letter_before):
        self.called_with = (sent_before, dead_letter_before)
        return 3


class TestNotificationCleanupService:
    @pytest.mark.asyncio
    async def test_cleanup_uses_configured_retention(self):
        repo = _FakeDeleteRepo()
        svc = NotificationCleanupService(
            _FakeTx(),
            repo,
            _FakeConfig({
                "notification.retention.sent_days": 30,
                "notification.retention.dead_letter_days": 90,
            }),
        )
        before = datetime.now(timezone.utc)
        await svc.cleanup()

        assert repo.called_with is not None
        sent_before, dead_before = repo.called_with
        # SENT giữ ngắn hơn DEAD_LETTER → cutoff SENT mới hơn (gần now hơn).
        assert sent_before > dead_before
        # Cutoff SENT ~ 30 ngày trước.
        assert 29 <= (before - sent_before).days <= 30
        assert 89 <= (before - dead_before).days <= 90
