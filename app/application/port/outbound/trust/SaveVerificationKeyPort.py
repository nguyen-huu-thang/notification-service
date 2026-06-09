from typing import Protocol
from datetime import datetime

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord


class SaveVerificationKeyPort(Protocol):
    async def save_all(self, keys: list[VerificationKeyRecord]) -> None: ...
    async def delete_expired(self, now: datetime) -> None: ...
