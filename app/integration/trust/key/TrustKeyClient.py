import logging
from datetime import datetime, timezone

from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord
from clients.trust import GetPublicKeysRequest, KeyDistributionServiceClient

_log = logging.getLogger(__name__)


class TrustKeyClient:
    """Thin adapter over the generated Trust KeyDistribution SDK client.

    The framework owns the channel lifecycle: the SDK client is injected with a
    dynamic-mTLS XimeGrpcChannel (configure_grpc_clients in config/grpc.py), so
    there is no manual channel/stub management and no reset on cert rotation -
    the channel rebuilds itself when the cert version changes.
    Adapter mỏng bọc client SDK sinh tự động cho KeyDistributionService của Trust.
    Framework quản lý vòng đời channel: client SDK được inject XimeGrpcChannel
    mTLS động (configure_grpc_clients trong config/grpc.py), nên không cần dựng
    channel/stub thủ công và không cần reset khi rotate cert - channel tự rebuild
    khi version cert đổi.
    """

    def __init__(self, config: RuntimeConfig, keys: KeyDistributionServiceClient) -> None:
        self._service_id = config.get("trust.service_id", "notification-service")
        self._keys = keys

    async def fetch_public_keys(self) -> list[VerificationKeyRecord]:
        """Fetch all valid public keys for this service from Trust Service."""
        response = await self._keys.get_public_keys(
            GetPublicKeysRequest(verifier_service_id=self._service_id)
        )
        return [self._map_key(k) for k in response.keys]

    @staticmethod
    def _map_key(dto) -> VerificationKeyRecord:
        # Trust sends activate_at/expires_at as epoch milliseconds.
        # Trust gửi activate_at/expires_at dạng epoch mili giây.
        return VerificationKeyRecord(
            key_id=dto.id,
            verifier_service_id=dto.verifier_service_id,
            public_key=dto.public_key,
            algorithm=dto.algorithm,
            key_size=dto.key_size,
            activate_at=datetime.fromtimestamp(dto.activate_at / 1000.0, tz=timezone.utc),
            expires_at=datetime.fromtimestamp(dto.expires_at / 1000.0, tz=timezone.utc),
        )
