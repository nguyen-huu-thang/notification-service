from typing import Protocol
from datetime import datetime

from app.domain.trust.Certificate import Certificate


class SaveCertificatePort(Protocol):
    async def save(self, cert: Certificate) -> None: ...
    async def delete_all(self) -> None: ...
    async def delete_expired(self, now: datetime, keep_id: str) -> None: ...
