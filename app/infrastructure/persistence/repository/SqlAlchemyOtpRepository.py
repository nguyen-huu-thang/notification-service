from xime.starters.sqlalchemy import AsyncSessionFactory

from app.domain.otp.OtpRecord import OtpRecord
from app.infrastructure.persistence.entity.OtpRecordEntity import OtpRecordEntity
from app.infrastructure.persistence.mapper.OtpRecordMapper import OtpRecordMapper


class SqlAlchemyOtpRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save(self, record: OtpRecord) -> None:
        session = self._sessions.current()
        await session.merge(OtpRecordMapper.to_entity(record))

    async def find_by_id(self, otp_id: bytes) -> OtpRecord | None:
        session = self._sessions.current()
        entity = await session.get(OtpRecordEntity, otp_id)
        return OtpRecordMapper.to_domain(entity) if entity else None
