import logging
from datetime import datetime, timezone

import grpc
import grpc.aio
from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.Certificate import Certificate
from app.integration.trust.generated.dependency.trust.cert.certificate_pb2 import RotateCertificateRequest
from app.integration.trust.generated.dependency.trust.cert.certificate_pb2_grpc import CertificateServiceStub

_log = logging.getLogger(__name__)


class GrpcTrustCertificateClient:
    """
    gRPC client for Trust Service CertificateService.
    Channel is created lazily after SSL context is available.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        self._host = config.get("trust.grpc.host", "localhost")
        self._port = int(config.get("trust.grpc.port", "9090"))
        self._channel: grpc.aio.Channel | None = None
        self._stub: CertificateServiceStub | None = None
        # ssl_context_provider injected after creation via set_ssl_provider()
        self._credentials: grpc.ChannelCredentials | None = None

    def set_credentials(self, credentials: grpc.ChannelCredentials) -> None:
        """Called by TrustSslContextProvider after cert is loaded."""
        self._credentials = credentials
        # Reset channel so next call creates a new one with the new credentials
        self._channel = None
        self._stub = None

    def _ensure_stub(self) -> CertificateServiceStub:
        if self._stub is None:
            if self._credentials is None:
                raise RuntimeError(
                    "GrpcTrustCertificateClient: SSL credentials not set. "
                    "Call set_credentials() after cert is loaded."
                )
            self._channel = grpc.aio.secure_channel(
                f"{self._host}:{self._port}",
                self._credentials,
            )
            self._stub = CertificateServiceStub(self._channel)
        return self._stub

    async def rotate_certificate(
        self,
        token_id: str,
        refresh_token: str,
        private_key: str,
    ) -> Certificate:
        stub = self._ensure_stub()
        request = RotateCertificateRequest(
            token_id=token_id,
            refresh_token=refresh_token,
            private_key=private_key,
        )
        response = await stub.RotateCertificate(request)
        return self._map_response(response)

    @staticmethod
    def _map_response(response) -> Certificate:
        cert_dto = response.certificate
        return Certificate(
            certificate_id=cert_dto.id,
            service_id=response.service_id,
            public_cert=cert_dto.public_cert,
            private_key=cert_dto.private_key,
            refresh_token_id=response.refresh_token_id,
            refresh_token=response.next_refresh_token,
            issued_at=datetime.fromtimestamp(response.issued_at / 1000.0, tz=timezone.utc),
            expires_at=datetime.fromtimestamp(response.expires_at / 1000.0, tz=timezone.utc),
        )

    async def pre_destroy(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None
