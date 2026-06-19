from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from xime.starters.sqlalchemy.session import AsyncSessionFactory

from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.infrastructure.persistence.entity.EmailNotificationEntity import EmailNotificationEntity
from app.infrastructure.persistence.mapper.EmailNotificationMapper import EmailNotificationMapper

# Statuses that the retry worker should pick up:
#   PENDING — saved but the send never completed (e.g. process crashed mid-send)
#   FAILED  — a previous attempt failed and a retry is scheduled
# Trạng thái worker cần nhặt: PENDING (lưu xong nhưng chưa gửi được) và FAILED (đã lên lịch retry).
_RETRYABLE = (NotificationStatus.PENDING.value, NotificationStatus.FAILED.value)


class SqlAlchemyNotificationRepository:

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save(self, notification: EmailNotification) -> None:
        # merge = upsert theo PK: insert lần đầu (PENDING), update các lần sau (SENT/FAILED...).
        session = self._sessions.current()
        entity = EmailNotificationMapper.to_entity(notification)
        await session.merge(entity)

    async def find_by_idempotency_key(
        self,
        caller_service_id: str | None,
        idempotency_key: str,
    ) -> EmailNotification | None:
        session = self._sessions.current()
        stmt = select(EmailNotificationEntity).where(
            EmailNotificationEntity.caller_service_id == (caller_service_id or ""),
            EmailNotificationEntity.idempotency_key == idempotency_key,
        )
        result = await session.execute(stmt)
        entity = result.scalars().first()
        return EmailNotificationMapper.to_domain(entity) if entity else None

    async def find_due_for_retry(
        self,
        now: datetime,
        limit: int,
    ) -> list[EmailNotification]:
        session = self._sessions.current()
        stmt = (
            select(EmailNotificationEntity)
            .where(
                EmailNotificationEntity.status.in_(_RETRYABLE),
                or_(
                    EmailNotificationEntity.next_retry_at.is_(None),
                    EmailNotificationEntity.next_retry_at <= now,
                ),
            )
            .order_by(EmailNotificationEntity.created_at)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return [EmailNotificationMapper.to_domain(e) for e in result.scalars().all()]

    async def delete_old(
        self,
        sent_before: datetime,
        dead_letter_before: datetime,
    ) -> int:
        session = self._sessions.current()
        stmt = delete(EmailNotificationEntity).where(
            or_(
                and_(
                    EmailNotificationEntity.status == NotificationStatus.SENT.value,
                    EmailNotificationEntity.sent_at < sent_before,
                ),
                and_(
                    EmailNotificationEntity.status == NotificationStatus.DEAD_LETTER.value,
                    EmailNotificationEntity.updated_at < dead_letter_before,
                ),
            )
        )
        result = await session.execute(stmt)
        return result.rowcount or 0
