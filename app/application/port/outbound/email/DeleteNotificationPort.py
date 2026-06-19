from datetime import datetime
from typing import Protocol


class DeleteNotificationPort(Protocol):
    async def delete_old(
        self,
        sent_before: datetime,
        dead_letter_before: datetime,
    ) -> int: ...
