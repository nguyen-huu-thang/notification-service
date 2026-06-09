import logging

from app.integration.trust.certificate.TrustCertificateSynchronizer import TrustCertificateSynchronizer
from app.integration.trust.key.TrustKeyClient import TrustKeyClient
from app.integration.trust.ssl.GrpcServerSslContextProvider import GrpcServerSslContextProvider

_log = logging.getLogger(__name__)


class CertRotationJob:
    """
    Periodic job: checks and rotates the mTLS certificate when it approaches expiry.
    After rotation, resets the key client channel and rebuilds server SSL credentials.
    """

    def __init__(
        self,
        cert_sync: TrustCertificateSynchronizer,
        key_client: TrustKeyClient,
        server_ssl: GrpcServerSslContextProvider,
    ) -> None:
        self._cert_sync = cert_sync
        self._key_client = key_client
        self._server_ssl = server_ssl

    async def run(self) -> None:
        _log.debug("CertRotationJob: checking certificate rotation.")
        await self._cert_sync.synchronize()
        # Force key client to pick up new SSL credentials on next request
        self._key_client.reset_channel()
        # Rebuild server credentials with potentially rotated cert
        self._server_ssl.reload()
