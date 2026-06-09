import logging
import threading

import grpc

from app.integration.trust.certificate.GrpcTrustCertificateClient import GrpcTrustCertificateClient
from app.integration.trust.certificate.TrustCertificateResolver import TrustCertificateResolver
from app.integration.trust.publicca.TrustRootCertificateResolver import TrustRootCertificateResolver
from app.integration.trust.ssl.PemNormalizer import to_certificate_pem, to_private_key_pem

_log = logging.getLogger(__name__)


class TrustSslContextProvider:
    """
    Builds and caches gRPC channel credentials for outgoing mTLS connections.
    Call reload() after every certificate update to push new credentials to all clients.
    """

    def __init__(
        self,
        cert_resolver: TrustCertificateResolver,
        root_ca_resolver: TrustRootCertificateResolver,
        cert_client: GrpcTrustCertificateClient,
    ) -> None:
        self._cert_resolver = cert_resolver
        self._root_ca_resolver = root_ca_resolver
        self._cert_client = cert_client
        self._creds: grpc.ChannelCredentials | None = None
        self._lock = threading.Lock()

    def reload(self) -> grpc.ChannelCredentials:
        """Rebuild credentials from the current cert + root CA, then update cert_client."""
        creds = self._build()
        with self._lock:
            self._creds = creds
        self._cert_client.set_credentials(creds)
        _log.debug("SSL channel credentials reloaded.")
        return creds

    def current(self) -> grpc.ChannelCredentials:
        with self._lock:
            creds = self._creds
        if creds is None:
            raise RuntimeError(
                "SSL channel credentials are not built yet. "
                "TrustCertificateSynchronizer must complete before this call."
            )
        return creds

    def _build(self) -> grpc.ChannelCredentials:
        cert = self._cert_resolver.current()
        root_ca = self._root_ca_resolver.current()
        return grpc.ssl_channel_credentials(
            root_certificates=root_ca.pem.encode("utf-8"),
            private_key=to_private_key_pem(cert.private_key).encode("utf-8"),
            certificate_chain=to_certificate_pem(cert.public_cert).encode("utf-8"),
        )
