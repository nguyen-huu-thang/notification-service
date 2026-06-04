from datetime import datetime

from pydantic import BaseModel


class SendOtpResult(BaseModel):
    otp_id: bytes
    expires_at: datetime
