from datetime import timezone

from app.domain.trust.Certificate import Certificate
from app.infrastructure.persistence.entity.TrustCertificateEntity import TrustCertificateEntity


class TrustCertificateMapper:

    @staticmethod
    def to_domain(entity: TrustCertificateEntity, private_key: str, refresh_token: str) -> Certificate:
        """
        private_key and refresh_token must be passed in already decrypted,
        because encryption/decryption is the repository's responsibility.
        """
        return Certificate(
            certificate_id=entity.certificate_id,
            service_id=entity.service_id,
            public_cert=entity.public_cert,
            private_key=private_key,
            refresh_token_id=entity.refresh_token_id,
            refresh_token=refresh_token,
            issued_at=entity.issued_at.replace(tzinfo=timezone.utc)
            if entity.issued_at.tzinfo is None
            else entity.issued_at,
            expires_at=entity.expires_at.replace(tzinfo=timezone.utc)
            if entity.expires_at.tzinfo is None
            else entity.expires_at,
        )

    @staticmethod
    def to_entity(domain: Certificate, encrypted_private_key: str, encrypted_refresh_token: str) -> TrustCertificateEntity:
        """
        encrypted_private_key and encrypted_refresh_token must already be encrypted
        before calling this method.
        """
        entity = TrustCertificateEntity()
        entity.certificate_id = domain.certificate_id
        entity.service_id = domain.service_id
        entity.public_cert = domain.public_cert
        entity.private_key = encrypted_private_key
        entity.refresh_token_id = domain.refresh_token_id
        entity.refresh_token = encrypted_refresh_token
        entity.issued_at = domain.issued_at
        entity.expires_at = domain.expires_at
        return entity
