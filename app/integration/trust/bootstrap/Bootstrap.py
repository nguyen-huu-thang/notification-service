from pathlib import Path

from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.Certificate import Certificate
from app.integration.trust.bootstrap.BootstrapLoader import BootstrapLoader
from app.integration.trust.bootstrap.BootstrapPayload import BootstrapPayload
from app.integration.trust.bootstrap.BootstrapValidator import BootstrapValidator


class Bootstrap:
    """
    Facade for bootstrap file access: load, validate, convert to Certificate, and delete.
    Used only at first startup to establish initial trust.
    """

    DEFAULT_BOOTSTRAP_PATH = Path("./runtime/security/bootstrap.txt")

    def __init__(self, config: RuntimeConfig) -> None:
        service_id = config.get("trust.service_id", "notification-service")
        path = Path(config.get("trust.bootstrap.path", str(self.DEFAULT_BOOTSTRAP_PATH)))
        self._service_id = service_id
        self._loader = BootstrapLoader(path)
        self._validator = BootstrapValidator()

    def exists(self) -> bool:
        return self._loader.exists()

    def load(self) -> Certificate:
        payload = self._loader.load()
        self._validator.validate(self._service_id, payload)
        return self._to_certificate(payload)

    def delete(self) -> None:
        self._loader.delete()

    @staticmethod
    def _to_certificate(payload: BootstrapPayload) -> Certificate:
        cert = payload.certificate
        return Certificate(
            certificate_id=cert.id,
            service_id=cert.service_id,
            public_cert=cert.public_cert,
            private_key=cert.private_key,
            refresh_token_id=payload.token_id,
            refresh_token=payload.refresh_token,
            issued_at=cert.issued_at_datetime(),
            expires_at=cert.expires_at_datetime(),
        )
