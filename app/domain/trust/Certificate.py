from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Certificate:
    certificate_id: str
    service_id: str
    public_cert: str       # PEM X.509
    private_key: str       # PEM PKCS#8
    refresh_token_id: str
    refresh_token: str     # one-time, bound to this cert
    issued_at: datetime
    expires_at: datetime

    def needs_rotation(self, now: datetime, threshold_days: int = 150) -> bool:
        return (now - self.issued_at).days >= threshold_days
