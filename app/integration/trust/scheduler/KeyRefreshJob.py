import logging

from app.integration.trust.key.VerificationKeySynchronizer import VerificationKeySynchronizer

_log = logging.getLogger(__name__)


class KeyRefreshJob:
    """Periodic job: fetches fresh verification keys from Trust Service."""

    def __init__(self, key_sync: VerificationKeySynchronizer) -> None:
        self._key_sync = key_sync

    async def run(self) -> None:
        _log.debug("KeyRefreshJob: refreshing verification keys.")
        await self._key_sync.synchronize()
