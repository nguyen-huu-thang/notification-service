from datetime import datetime, timezone

import pytest

from app.application.service.email.RetrySendService import RetrySendService
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FakeConfig:
    def get(self, key, default=None):
        return default


class _FakeTx:
    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeRepo:
    def __init__(self, due):
        self._due = due
        self.saved = []

    async def find_due_for_retry(self, now, limit):
        return list(self._due)

    async def save(self, notification):
        self.saved.append(notification)


class _FakeDelivery:
    def __init__(self):
        self.delivered = []

    async def deliver(self, notification, now):
        self.delivered.append(notification)
        return notification.mark_sent(now)


def _notification() -> EmailNotification:
    return EmailNotification.create(EmailAddress("u@e.com"), "S", "<p>b</p>", _NOW)


class TestRetrySendService:
    @pytest.mark.asyncio
    async def test_processes_each_due_notification(self):
        due = [_notification(), _notification()]
        repo = _FakeRepo(due)
        delivery = _FakeDelivery()
        svc = RetrySendService(_FakeTx(), repo, repo, delivery, _FakeConfig())

        await svc.process_due()

        assert len(delivery.delivered) == 2
        assert len(repo.saved) == 2
        assert all(n.status == NotificationStatus.SENT for n in repo.saved)

    @pytest.mark.asyncio
    async def test_no_due_does_nothing(self):
        repo = _FakeRepo([])
        delivery = _FakeDelivery()
        svc = RetrySendService(_FakeTx(), repo, repo, delivery, _FakeConfig())

        await svc.process_due()

        assert delivery.delivered == []
        assert repo.saved == []
