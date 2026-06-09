import logging
from datetime import datetime, timezone

import grpc.aio
from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord
from app.integration.trust.generated.dependency.trust.key.key_distribution_pb2 import GetPublicKeysRequest
from app.integration.trust.generated.dependency.trust.key.key_distribution_pb2_grpc import KeyDistributionServiceStub
from app.integration.trust.ssl.TrustSslContextProvider import TrustSslContextProvider

_log = logging.getLogger(__name__)


class TrustKeyClient:
    """
    gRPC client for Trust Service KeyDistributionService.
    Channel is created lazily after SSL context is available.
    """

    def __init__(self, config: RuntimeConfig, ssl_provider: TrustSslContextProvider) -> None:
        self._host = config.get("trust.grpc.host", "localhost")
        self._port = int(config.get("trust.grpc.port", "9090"))
        self._service_id = config.get("trust.service_id", "notification-service")
        self._ssl = ssl_provider
        self._channel: grpc.aio.Channel | None = None
        self._stub: KeyDistributionServiceStub | None = None

    def _ensure_stub(self) -> KeyDistributionServiceStub:
        if self._stub is None:
            self._channel = grpc.aio.secure_channel(
                f"{self._host}:{self._port}",
                self._ssl.current(),
            )
            self._stub = KeyDistributionServiceStub(self._channel)
        return self._stub

    async def fetch_public_keys(self) -> list[VerificationKeyRecord]:
        """Fetch all valid public keys for this service from Trust Service."""
        stub = self._ensure_stub()
        request = GetPublicKeysRequest(verifier_service_id=self._service_id)
        response = await stub.GetPublicKeys(request)
        return [self._map_key(k) for k in response.keys]

    @staticmethod
    def _map_key(dto) -> VerificationKeyRecord:
        return VerificationKeyRecord(
            key_id=dto.id,
            verifier_service_id=dto.verifier_service_id,
            public_key=dto.public_key,
            algorithm=dto.algorithm,
            key_size=dto.key_size,
            activate_at=datetime.fromtimestamp(dto.activate_at / 1000.0, tz=timezone.utc),
            expires_at=datetime.fromtimestamp(dto.expires_at / 1000.0, tz=timezone.utc),
        )

    def reset_channel(self) -> None:
        """Force channel recreation on next request, picking up refreshed SSL credentials."""
        self._channel = None
        self._stub = None

    async def pre_destroy(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None
