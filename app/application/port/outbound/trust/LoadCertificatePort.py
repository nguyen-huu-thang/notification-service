from typing import Protocol

from app.domain.trust.Certificate import Certificate


class LoadCertificatePort(Protocol):
    async def find_latest(self) -> Certificate | None: ...
