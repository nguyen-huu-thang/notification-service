from datetime import datetime, timezone

import pytest

from app.application.service.email.EmailDeliveryService import EmailDeliveryService
from app.application.service.retry.RetryPolicy import RetryPolicy
from app.common.constants.NotificationStatus import NotificationStatus
from app.common.exception.AppException import PrivateError, PublicError, SystemError
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _FakeConfig:
    def get(self, key, default=None):
        return default


class _FakeEmailSender:
    def __init__(self, side_effect=None):
        self.sent = []
        self._side_effect = side_effect

    async def send(self, to, subject, body):
        if self._side_effect is not None:
            raise self._side_effect
        self.sent.append((to, subject, body))


def _notification() -> EmailNotification:
    return EmailNotification.create(EmailAddress("u@e.com"), "S", "<p>b</p>", _NOW)


def _service(side_effect=None) -> EmailDeliveryService:
    return EmailDeliveryService(_FakeEmailSender(side_effect), RetryPolicy(_FakeConfig()))


class TestEmailDeliveryService:
    @pytest.mark.asyncio
    async def test_success_marks_sent(self):
        result = await _service().deliver(_notification(), _NOW)
        assert result.status == NotificationStatus.SENT
        assert result.sent_at == _NOW

    @pytest.mark.asyncio
    async def test_transient_system_error_schedules_retry(self):
        result = await _service(SystemError("E084000")).deliver(_notification(), _NOW)
        assert result.status == NotificationStatus.FAILED
        assert result.next_retry_at is not None
        assert result.last_error_code == "E084000"

    @pytest.mark.asyncio
    async def test_smtp_config_private_error_schedules_retry(self):
        result = await _service(PrivateError("E080002")).deliver(_notification(), _NOW)
        assert result.status == NotificationStatus.FAILED
        assert result.last_error_code == "E080002"

    @pytest.mark.asyncio
    async def test_recipient_refused_public_error_dead_letters(self):
        result = await _service(PublicError("E087000")).deliver(_notification(), _NOW)
        assert result.status == NotificationStatus.DEAD_LETTER
        assert result.last_error_code == "E087000"
