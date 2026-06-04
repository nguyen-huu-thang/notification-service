from typing import Protocol

from app.domain.otp.OtpRecord import OtpRecord


class LoadOtpPort(Protocol):
    async def find_by_id(self, otp_id: bytes) -> OtpRecord | None: ...
