from typing import Protocol

from app.domain.otp.OtpRecord import OtpRecord


class SaveOtpPort(Protocol):
    async def save(self, record: OtpRecord) -> None: ...
