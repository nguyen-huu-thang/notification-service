from datetime import datetime, timezone

from app.integration.trust.bootstrap.BootstrapPayload import BootstrapPayload


class BootstrapValidator:
    """Validates bootstrap payload before using it to establish trust."""

    def validate(self, service_id: str, payload: BootstrapPayload) -> None:
        cert = payload.certificate

        if cert.status != "ACTIVE":
            raise ValueError(
                f"Bootstrap certificate status is not ACTIVE: {cert.status}"
            )

        if cert.service_id != service_id:
            raise ValueError(
                f"Bootstrap certificate service_id mismatch: "
                f"expected '{service_id}', got '{cert.service_id}'"
            )

        now = datetime.now(timezone.utc)
        if cert.expires_at_datetime() <= now:
            raise ValueError(
                f"Bootstrap certificate has expired: expires_at={cert.expires_at}"
            )

        if not cert.public_cert.strip():
            raise ValueError("Bootstrap certificate public_cert is empty")

        if not cert.private_key.strip():
            raise ValueError("Bootstrap certificate private_key is empty")

        if not payload.token_id.strip():
            raise ValueError("Bootstrap token_id is empty")

        if not payload.refresh_token.strip():
            raise ValueError("Bootstrap refresh_token is empty")
