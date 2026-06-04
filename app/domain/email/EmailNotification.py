from dataclasses import dataclass, replace
from datetime import datetime

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus


@dataclass(frozen=True)
class EmailNotification:
    notification_id: bytes
    recipient: str
    subject: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None = None

    def mark_sent(self, now: datetime) -> "EmailNotification":
        return replace(self, status=NotificationStatus.SENT, sent_at=now)

    def mark_failed(self) -> "EmailNotification":
        return replace(self, status=NotificationStatus.FAILED)
