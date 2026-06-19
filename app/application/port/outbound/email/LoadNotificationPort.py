from datetime import datetime
from typing import Protocol

from app.domain.email.model.EmailNotification import EmailNotification


class LoadNotificationPort(Protocol):
    async def find_by_idempotency_key(
        self,
        caller_service_id: str | None,
        idempotency_key: str,
    ) -> EmailNotification | None: ...

    async def find_due_for_retry(
        self,
        now: datetime,
        limit: int,
    ) -> list[EmailNotification]: ...
