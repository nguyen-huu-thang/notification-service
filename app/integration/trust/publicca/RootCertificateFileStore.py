from pathlib import Path

from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.RootCertificate import RootCertificate


class RootCertificateFileStore:
    """Reads the Root CA certificate from a PEM file on disk."""

    def __init__(self, config: RuntimeConfig) -> None:
        self._path = Path(config.get("trust.ca_cert.path", "./runtime/security/ca.pem"))

    def load(self) -> RootCertificate:
        if not self._path.exists():
            raise RuntimeError(
                f"\n"
                f"==================================================\n"
                f"FATAL: Root CA certificate file not found.\n"
                f"Path: {self._path}\n"
                f"==================================================\n"
                f"Place the CA cert PEM at the configured path\n"
                f"or set trust.ca_cert.path in application.yml.\n"
            )
        pem = self._path.read_text(encoding="utf-8").strip()
        return RootCertificate(pem=pem)
