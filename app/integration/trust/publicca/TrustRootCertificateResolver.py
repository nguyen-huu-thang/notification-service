from app.domain.trust.RootCertificate import RootCertificate


class TrustRootCertificateResolver:
    """In-memory cache for the Root CA certificate."""

    def __init__(self) -> None:
        self._cert: RootCertificate | None = None

    def update(self, cert: RootCertificate) -> None:
        self._cert = cert

    def current(self) -> RootCertificate:
        cert = self._cert
        if cert is None:
            raise RuntimeError(
                "Root CA certificate is not loaded. "
                "TrustRootCertificateInitializer.initialize() must run before this call."
            )
        return cert
