import logging
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import delete, select
from xime.core.config.runtime import RuntimeConfig
from xime.starters.sqlalchemy.session import AsyncSessionFactory

from app.domain.trust.Certificate import Certificate
from app.infrastructure.persistence.entity.TrustCertificateEntity import TrustCertificateEntity
from app.infrastructure.persistence.mapper.TrustCertificateMapper import TrustCertificateMapper

_log = logging.getLogger(__name__)


class TrustCertificateRepository:
    """
    Persists the mTLS certificate.
    private_key and refresh_token are encrypted with Fernet before storage.

    Encryption key resolution (first match wins):
      1. TRUST_CERT_ENCRYPTION_KEY environment variable (ops override)
      2. trust.cert_encryption_key in application.yml (default for dev)
    The key must stay stable across restarts, otherwise stored certs cannot
    be decrypted. It is a url-safe base64-encoded 32-byte Fernet key.
    """

    def __init__(self, sessions: AsyncSessionFactory, config: RuntimeConfig) -> None:
        self._sessions = sessions
        key = os.environ.get("TRUST_CERT_ENCRYPTION_KEY") or config.get("trust.cert_encryption_key")
        if not key:
            raise RuntimeError(
                "Trust certificate encryption key is not configured. "
                "Set the TRUST_CERT_ENCRYPTION_KEY env var or trust.cert_encryption_key in application.yml. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    async def find_latest(self) -> Certificate | None:
        session = self._sessions.current()
        stmt = (
            select(TrustCertificateEntity)
            .order_by(TrustCertificateEntity.issued_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        private_key = self._decrypt(entity.private_key)
        refresh_token = self._decrypt(entity.refresh_token)
        return TrustCertificateMapper.to_domain(entity, private_key, refresh_token)

    async def save(self, cert: Certificate) -> None:
        session = self._sessions.current()
        encrypted_key = self._encrypt(cert.private_key)
        encrypted_token = self._encrypt(cert.refresh_token)
        entity = TrustCertificateMapper.to_entity(cert, encrypted_key, encrypted_token)
        await session.merge(entity)

    async def delete_all(self) -> None:
        session = self._sessions.current()
        await session.execute(delete(TrustCertificateEntity))

    async def delete_expired(self, now: datetime, keep_id: str) -> None:
        session = self._sessions.current()
        stmt = delete(TrustCertificateEntity).where(
            TrustCertificateEntity.expires_at < now,
            TrustCertificateEntity.certificate_id != keep_id,
        )
        await session.execute(stmt)

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
