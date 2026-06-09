import logging
import threading

import grpc

from app.integration.trust.certificate.TrustCertificateResolver import TrustCertificateResolver
from app.integration.trust.publicca.TrustRootCertificateResolver import TrustRootCertificateResolver
from app.integration.trust.ssl.PemNormalizer import to_certificate_pem, to_private_key_pem

_log = logging.getLogger(__name__)


class GrpcServerSslContextProvider:
    """
    Builds and caches gRPC server credentials for incoming mTLS connections.
    Uses mutual TLS: clients must present a certificate signed by the same root CA.
    """

    def __init__(
        self,
        cert_resolver: TrustCertificateResolver,
        root_ca_resolver: TrustRootCertificateResolver,
    ) -> None:
        self._cert_resolver = cert_resolver
        self._root_ca_resolver = root_ca_resolver
        self._creds: grpc.ServerCredentials | None = None
        self._lock = threading.Lock()

    def reload(self) -> grpc.ServerCredentials:
        """Rebuild server credentials from the current cert + root CA."""
        creds = self._build()
        with self._lock:
            self._creds = creds
        _log.debug("SSL server credentials reloaded.")
        return creds

    def current(self) -> grpc.ServerCredentials:
        with self._lock:
            creds = self._creds
        if creds is None:
            raise RuntimeError(
                "SSL server credentials are not built yet. "
                "TrustCertificateSynchronizer must complete before this call."
            )
        return creds

    def _build(self) -> grpc.ServerCredentials:
        cert = self._cert_resolver.current()
        root_ca = self._root_ca_resolver.current()
        return grpc.ssl_server_credentials(
            private_key_certificate_chain_pairs=[(
                to_private_key_pem(cert.private_key).encode("utf-8"),
                to_certificate_pem(cert.public_cert).encode("utf-8"),
            )],
            root_certificates=root_ca.pem.encode("utf-8"),
            require_client_auth=True,
        )
