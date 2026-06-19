from __future__ import annotations

import logging
from datetime import datetime, timezone

from xime.core.config.runtime import RuntimeConfig
from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.email.LoadNotificationPort import LoadNotificationPort
from app.application.port.outbound.email.SaveNotificationPort import SaveNotificationPort
from app.application.service.email.EmailDeliveryService import EmailDeliveryService

_log = logging.getLogger(__name__)

_DEFAULT_BATCH_SIZE = 50


class RetrySendService:
    """Worker logic: gửi lại các notification PENDING/FAILED đã đến hạn.

    Đọc batch trong transaction, gửi từng cái NGOÀI transaction (không giữ tx khi
    gọi SMTP), lưu kết quả trong transaction riêng. Dùng chung EmailDeliveryService
    với SendEmailUseCase nên logic SENT/FAILED/DEAD_LETTER đồng nhất.
    """

    def __init__(
        self,
        transaction: TransactionManager,
        load_notification: LoadNotificationPort,
        save_notification: SaveNotificationPort,
        delivery: EmailDeliveryService,
        config: RuntimeConfig,
    ) -> None:
        self._tx = transaction
        self._load = load_notification
        self._save = save_notification
        self._delivery = delivery
        self._batch_size: int = config.get("notification.retry.batch_size", _DEFAULT_BATCH_SIZE)

    async def process_due(self) -> None:
        now = datetime.now(timezone.utc)
        async with self._tx():
            due = await self._load.find_due_for_retry(now, self._batch_size)

        if not due:
            return

        for notification in due:
            delivered = await self._delivery.deliver(notification, datetime.now(timezone.utc))
            async with self._tx():
                await self._save.save(delivered)

        _log.info("Retry batch processed: %d notifications", len(due))
