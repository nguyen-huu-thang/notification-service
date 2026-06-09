from typing import Protocol
from datetime import datetime

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord


class LoadVerificationKeyPort(Protocol):
    async def find_valid(self, now: datetime) -> list[VerificationKeyRecord]: ...
