from datetime import datetime

from sqlalchemy import delete, select
from xime.starters.sqlalchemy.session import AsyncSessionFactory

from app.domain.trust.VerificationKeyRecord import VerificationKeyRecord
from app.infrastructure.persistence.entity.TrustVerificationKeyEntity import TrustVerificationKeyEntity
from app.infrastructure.persistence.mapper.TrustVerificationKeyMapper import TrustVerificationKeyMapper


class TrustVerificationKeyRepository:

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def find_valid(self, now: datetime) -> list[VerificationKeyRecord]:
        session = self._sessions.current()
        stmt = select(TrustVerificationKeyEntity).where(
            TrustVerificationKeyEntity.expires_at > now,
            TrustVerificationKeyEntity.activate_at <= now,
        )
        result = await session.execute(stmt)
        return [TrustVerificationKeyMapper.to_domain(e) for e in result.scalars().all()]

    async def save_all(self, keys: list[VerificationKeyRecord]) -> None:
        session = self._sessions.current()
        for key in keys:
            entity = TrustVerificationKeyMapper.to_entity(key)
            await session.merge(entity)

    async def delete_expired(self, now: datetime) -> None:
        session = self._sessions.current()
        stmt = delete(TrustVerificationKeyEntity).where(
            TrustVerificationKeyEntity.expires_at < now,
        )
        await session.execute(stmt)
