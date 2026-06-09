import logging

from app.integration.trust.key.TrustKeyCleanup import TrustKeyCleanup

_log = logging.getLogger(__name__)


class KeyCleanupJob:
    """Periodic job: removes expired verification keys from DB and in-memory cache."""

    def __init__(self, key_cleanup: TrustKeyCleanup) -> None:
        self._key_cleanup = key_cleanup

    async def run(self) -> None:
        _log.debug("KeyCleanupJob: cleaning up expired verification keys.")
        await self._key_cleanup.cleanup()
