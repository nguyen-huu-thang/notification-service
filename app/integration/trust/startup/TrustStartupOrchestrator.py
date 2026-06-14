import logging

from app.integration.trust.certificate.TrustCertificateSynchronizer import TrustCertificateSynchronizer
from app.integration.trust.key.VerificationKeySynchronizer import VerificationKeySynchronizer
from app.integration.trust.publicca.TrustRootCertificateInitializer import TrustRootCertificateInitializer

_log = logging.getLogger(__name__)


class TrustStartupOrchestrator:
    """
    Runs the full trust bootstrap sequence at application startup.

    Ordering is strict:
      1. Load root CA certificate from disk       → enables cert + key verification
      2. Synchronize mTLS certificate              → populates the cert resolver
      3. Synchronize verification keys             → enables JWT signature verification

    Inbound mTLS no longer needs a build step here: the gRPC server reads the
    cert lazily from TrustGrpcCertificateProvider on every new handshake. Step 2
    must still run before the adapter serves its first request, because the
    provider reads the resolver that step 2 populates.
    mTLS vào không còn bước build ở đây: server gRPC đọc cert lười từ
    TrustGrpcCertificateProvider ở mỗi handshake mới. Bước 2 vẫn phải chạy trước
    khi adapter phục vụ request đầu tiên, vì provider đọc resolver mà bước 2 nạp.
    """

    def __init__(
        self,
        root_ca_init: TrustRootCertificateInitializer,
        cert_sync: TrustCertificateSynchronizer,
        key_sync: VerificationKeySynchronizer,
    ) -> None:
        self._root_ca_init = root_ca_init
        self._cert_sync = cert_sync
        self._key_sync = key_sync

    async def post_construct(self) -> None:
        _log.info("Trust startup: loading root CA certificate.")
        self._root_ca_init.initialize()

        _log.info("Trust startup: synchronizing mTLS certificate.")
        await self._cert_sync.synchronize_on_startup()

        _log.info("Trust startup: synchronizing verification keys.")
        await self._key_sync.synchronize()

        _log.info("Trust startup complete.")
