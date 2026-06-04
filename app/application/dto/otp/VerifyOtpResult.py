from pydantic import BaseModel


class VerifyOtpResult(BaseModel):
    success: bool
