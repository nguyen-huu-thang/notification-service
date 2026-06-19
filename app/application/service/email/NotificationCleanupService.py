from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from xime.core.config.runtime import RuntimeConfig
from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.email.DeleteNotificationPort import DeleteNotificationPort

_log = logging.getLogger(__name__)

_DEFAULT_SENT_DAYS = 30
_DEFAULT_DEAD_LETTER_DAYS = 90


class NotificationCleanupService:
    """Dọn dữ liệu cũ trong bảng email_notifications theo retention (cũng xóa PII cũ).

    - SENT cũ hơn `sent_days` ngày.
    - DEAD_LETTER cũ hơn `dead_letter_days` ngày.
    """

    def __init__(
        self,
        transaction: TransactionManager,
        delete_notification: DeleteNotificationPort,
        config: RuntimeConfig,
    ) -> None:
        self._tx = transaction
        self._delete = delete_notification
        self._sent_days: int = config.get("notification.retention.sent_days", _DEFAULT_SENT_DAYS)
        self._dead_letter_days: int = config.get(
            "notification.retention.dead_letter_days", _DEFAULT_DEAD_LETTER_DAYS
        )

    async def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        sent_before = now - timedelta(days=self._sent_days)
        dead_letter_before = now - timedelta(days=self._dead_letter_days)

        async with self._tx():
            removed = await self._delete.delete_old(sent_before, dead_letter_before)

        _log.info("Notification cleanup removed %d rows", removed)
