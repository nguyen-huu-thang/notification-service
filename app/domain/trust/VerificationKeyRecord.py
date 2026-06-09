from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VerificationKeyRecord:
    """Persistent record of a verification key — stored in DB as local cache."""

    key_id: str
    verifier_service_id: str
    public_key: str       # PEM — no private key (verify-only service)
    algorithm: str        # RS256, ES256, EdDSA
    key_size: int
    activate_at: datetime
    expires_at: datetime

    def is_valid(self, now: datetime) -> bool:
        return now < self.expires_at and now >= self.activate_at
