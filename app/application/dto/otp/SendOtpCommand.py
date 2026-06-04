from pydantic import BaseModel

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType


class SendOtpCommand(BaseModel):
    channel: NotificationChannel
    target: str
    otp_type: OtpType
    context_id: bytes | None = None
