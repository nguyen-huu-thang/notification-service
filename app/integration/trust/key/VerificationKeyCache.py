import threading
from datetime import datetime

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord


class VerificationKeyCache:
    """In-memory cache for verification key records used in JWT signature verification."""

    def __init__(self) -> None:
        self._cache: dict[str, VerificationKeyRecord] = {}
        self._lock = threading.Lock()

    def resolve(self, key_id: str, now: datetime) -> VerificationKeyRecord | None:
        key = self._cache.get(key_id)
        return key if key and key.is_valid(now) else None

    def update(self, keys: list[VerificationKeyRecord]) -> None:
        with self._lock:
            for key in keys:
                self._cache[key.key_id] = key

    def clean_expired(self, now: datetime) -> None:
        with self._lock:
            self._cache = {k: v for k, v in self._cache.items() if v.is_valid(now)}
