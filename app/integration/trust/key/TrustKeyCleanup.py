import logging
from datetime import datetime, timezone

from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.trust.SaveVerificationKeyPort import SaveVerificationKeyPort
from app.integration.trust.key.VerificationKeyCache import VerificationKeyCache

_log = logging.getLogger(__name__)


class TrustKeyCleanup:
    """Removes expired verification keys from DB and cache."""

    def __init__(
        self,
        transaction: TransactionManager,
        save_key_port: SaveVerificationKeyPort,
        cache: VerificationKeyCache,
    ) -> None:
        self._tx = transaction
        self._save = save_key_port
        self._cache = cache

    async def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        async with self._tx():
            await self._save.delete_expired(now)
        self._cache.clean_expired(now)
        _log.debug("Expired verification keys cleaned up at %s.", now.isoformat())
