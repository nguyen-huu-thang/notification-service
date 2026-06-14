import logging
from datetime import datetime, timezone

from xime.core.exception.framework import RemoteServiceUnavailable
from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.trust.LoadVerificationKeyPort import LoadVerificationKeyPort
from app.application.port.outbound.trust.SaveVerificationKeyPort import SaveVerificationKeyPort
from app.integration.trust.key.TrustKeyClient import TrustKeyClient
from app.integration.trust.key.VerificationKeyCache import VerificationKeyCache

_log = logging.getLogger(__name__)


class VerificationKeySynchronizer:
    """
    Keeps verification keys in sync between Trust Service, DB, and in-memory cache.
    - On startup: fetch from Trust Service → save to DB → update cache.
      If Trust Service is unavailable, fall back to DB.
    - Periodic: same flow, run by scheduler.
    """

    def __init__(
        self,
        transaction: TransactionManager,
        load_key_port: LoadVerificationKeyPort,
        save_key_port: SaveVerificationKeyPort,
        cache: VerificationKeyCache,
        key_client: TrustKeyClient,
    ) -> None:
        self._tx = transaction
        self._load = load_key_port
        self._save = save_key_port
        self._cache = cache
        self._client = key_client

    async def synchronize(self) -> None:
        """Fetch keys from Trust Service, persist, and refresh cache. Falls back to DB on error."""
        try:
            keys = await self._client.fetch_public_keys()
            if not keys:
                _log.warning("Trust Service returned no verification keys.")
                return
            async with self._tx():
                await self._save.save_all(keys)
            self._cache.update(keys)
            _log.info("Verification keys synchronized from Trust Service: %d keys.", len(keys))
        except RemoteServiceUnavailable:
            # Trust Service not running — expected in dev/partial deployments.
            # No realtime dependency on Trust: fall back to DB-cached keys quietly.
            # Trust không chạy — bình thường khi dev/triển khai từng phần. Không
            # phụ thuộc realtime vào Trust: lặng lẽ dùng key đã cache trong DB.
            _log.debug("Trust Service is not reachable — using keys from DB.")
            await self._load_from_db()
        except Exception as e:
            _log.warning(
                "Failed to fetch verification keys from Trust Service — falling back to DB. Error: %s", e
            )
            await self._load_from_db()

    async def _load_from_db(self) -> None:
        now = datetime.now(timezone.utc)
        async with self._tx():
            keys = await self._load.find_valid(now)
        self._cache.update(keys)
        _log.info("Verification keys loaded from DB: %d keys.", len(keys))
