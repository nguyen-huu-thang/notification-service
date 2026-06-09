import threading

from app.domain.trust.Certificate import Certificate


class TrustCertificateResolver:
    """In-memory cache for the current mTLS certificate."""

    def __init__(self) -> None:
        self._cert: Certificate | None = None
        self._lock = threading.Lock()

    def update(self, cert: Certificate) -> None:
        with self._lock:
            self._cert = cert

    def current(self) -> Certificate:
        cert = self._cert
        if cert is None:
            raise RuntimeError(
                "mTLS certificate is not loaded. "
                "TrustCertificateSynchronizer.synchronize_on_startup() must run first."
            )
        return cert

    def current_or_none(self) -> Certificate | None:
        return self._cert
