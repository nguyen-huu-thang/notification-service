import logging

from app.integration.trust.publicca.RootCertificateFileStore import RootCertificateFileStore
from app.integration.trust.publicca.TrustRootCertificateResolver import TrustRootCertificateResolver

_log = logging.getLogger(__name__)


class TrustRootCertificateInitializer:
    """Loads Root CA cert from file into resolver on startup."""

    def __init__(
        self,
        file_store: RootCertificateFileStore,
        resolver: TrustRootCertificateResolver,
    ) -> None:
        self._store = file_store
        self._resolver = resolver

    def initialize(self) -> None:
        cert = self._store.load()
        self._resolver.update(cert)
        _log.info("Root CA certificate loaded successfully.")
