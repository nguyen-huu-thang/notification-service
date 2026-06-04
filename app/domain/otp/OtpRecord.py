from dataclasses import dataclass, replace
from datetime import datetime

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType


@dataclass(frozen=True)
class OtpRecord:
    otp_id: bytes
    channel: NotificationChannel
    target: str
    otp_hash: str
    otp_type: OtpType
    context_id: bytes | None
    expires_at: datetime
    is_used: bool
    created_at: datetime

    def mark_used(self) -> "OtpRecord":
        return replace(self, is_used=True)

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
