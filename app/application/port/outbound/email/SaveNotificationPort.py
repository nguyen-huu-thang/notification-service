from typing import Protocol

from app.domain.email.model.EmailNotification import EmailNotification


class SaveNotificationPort(Protocol):
    async def save(self, notification: EmailNotification) -> None: ...
