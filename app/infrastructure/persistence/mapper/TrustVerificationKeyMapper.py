from datetime import timezone

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord
from app.infrastructure.persistence.entity.TrustVerificationKeyEntity import TrustVerificationKeyEntity


class TrustVerificationKeyMapper:

    @staticmethod
    def to_domain(entity: TrustVerificationKeyEntity) -> VerificationKeyRecord:
        def _aware(dt):
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

        return VerificationKeyRecord(
            key_id=entity.key_id,
            verifier_service_id=entity.verifier_service_id,
            public_key=entity.public_key,
            algorithm=entity.algorithm,
            key_size=entity.key_size,
            activate_at=_aware(entity.activate_at),
            expires_at=_aware(entity.expires_at),
        )

    @staticmethod
    def to_entity(domain: VerificationKeyRecord) -> TrustVerificationKeyEntity:
        entity = TrustVerificationKeyEntity()
        entity.key_id = domain.key_id
        entity.verifier_service_id = domain.verifier_service_id
        entity.public_key = domain.public_key
        entity.algorithm = domain.algorithm
        entity.key_size = domain.key_size
        entity.activate_at = domain.activate_at
        entity.expires_at = domain.expires_at
        return entity
