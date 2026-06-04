from pydantic import BaseModel


class VerifyOtpCommand(BaseModel):
    otp_id: bytes
    code: str
