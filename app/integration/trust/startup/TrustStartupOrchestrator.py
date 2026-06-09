import logging
from pathlib import Path

from app.integration.trust.certificate.TrustCertificateResolver import TrustCertificateResolver
from app.integration.trust.certificate.TrustCertificateSynchronizer import TrustCertificateSynchronizer
from app.integration.trust.key.VerificationKeySynchronizer import VerificationKeySynchronizer
from app.integration.trust.publicca.TrustRootCertificateInitializer import TrustRootCertificateInitializer
from app.integration.trust.ssl.GrpcServerSslContextProvider import GrpcServerSslContextProvider
from app.integration.trust.ssl.PemNormalizer import to_certificate_pem, to_private_key_pem

_log = logging.getLogger(__name__)


class TrustStartupOrchestrator:
    """
    Runs the full trust bootstrap sequence at application startup.

    Ordering is strict:
      1. Load root CA certificate from disk       → enables cert + key verification
      2. Synchronize mTLS certificate              → establishes outbound mTLS identity
      3. Build server SSL credentials              → enables inbound mTLS connections
      4. Write PEM files to disk                   → GrpcAdapter reads them when starting
      5. Synchronize verification keys             → enables JWT signature verification
    """

    def __init__(
        self,
        root_ca_init: TrustRootCertificateInitializer,
        cert_sync: TrustCertificateSynchronizer,
        server_ssl: GrpcServerSslContextProvider,
        cert_resolver: TrustCertificateResolver,
        key_sync: VerificationKeySynchronizer,
    ) -> None:
        self._root_ca_init = root_ca_init
        self._cert_sync = cert_sync
        self._server_ssl = server_ssl
        self._cert_resolver = cert_resolver
        self._key_sync = key_sync

    async def post_construct(self) -> None:
        _log.info("Trust startup: loading root CA certificate.")
        self._root_ca_init.initialize()

        _log.info("Trust startup: synchronizing mTLS certificate.")
        await self._cert_sync.synchronize_on_startup()

        _log.info("Trust startup: building server SSL credentials.")
        self._server_ssl.reload()

        # Write PEM files to disk so GrpcAdapter can read them at add_secure_port time.
        # post_construct() runs before GrpcAdapter.start() — guaranteed by Xime Framework.
        # Ghi PEM ra disk để GrpcAdapter đọc khi add_secure_port.
        # post_construct() chạy trước GrpcAdapter.start() — Xime Framework đảm bảo điều này.
        _log.info("Trust startup: writing server PEM files for GrpcAdapter.")
        self._write_server_pem_files()

        _log.info("Trust startup: synchronizing verification keys.")
        await self._key_sync.synchronize()

        _log.info("Trust startup complete.")

    def _write_server_pem_files(self) -> None:
        """Write cert + key PEM to runtime/security/ for GrpcAdapter file-based TLS.
        Ghi cert + key PEM ra runtime/security/ để GrpcAdapter dùng TLS dạng file.
        """
        cert = self._cert_resolver.current()
        cert_dir = Path("./runtime/security")
        cert_dir.mkdir(parents=True, exist_ok=True)

        (cert_dir / "server.crt").write_text(
            to_certificate_pem(cert.public_cert), encoding="utf-8"
        )
        (cert_dir / "server.key").write_text(
            to_private_key_pem(cert.private_key), encoding="utf-8"
        )
        _log.debug("Server PEM files written to %s", cert_dir)
