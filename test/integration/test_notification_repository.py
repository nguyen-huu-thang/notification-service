"""
Integration tests — SqlAlchemyNotificationRepository trên SQLite thật:
  - save (insert + upsert qua merge)
  - find_by_idempotency_key (tìm thấy / không / scope theo caller)
  - find_due_for_retry (chọn đúng PENDING + FAILED đến hạn, loại trừ phần còn lại, order + limit)
  - delete_old (xóa SENT/DEAD_LETTER cũ, giữ bản ghi mới và đang xử lý)
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import update

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.infrastructure.persistence.entity.EmailNotificationEntity import EmailNotificationEntity
from app.infrastructure.persistence.repository.email.SqlAlchemyNotificationRepository import (
    SqlAlchemyNotificationRepository,
)
from test.integration.conftest import FakeSessionFactory

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def repo(db_session) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(FakeSessionFactory(db_session))


def _make(
    status: NotificationStatus,
    *,
    idempotency_key: str | None = None,
    caller: str | None = None,
    created_at: datetime = _NOW,
    next_retry_at: datetime | None = None,
    sent_at: datetime | None = None,
    attempts: int = 0,
    notification_id=None,
) -> EmailNotification:
    return EmailNotification(
        notification_id=notification_id or IdFactory.generate(),
        recipient=EmailAddress("user@example.com"),
        subject="S",
        body="<p>b</p>",
        channel=NotificationChannel.EMAIL,
        status=status,
        created_at=created_at,
        attempts=attempts,
        next_retry_at=next_retry_at,
        last_error_code=None,
        idempotency_key=idempotency_key,
        caller_service_id=caller,
        sent_at=sent_at,
    )


# ── save + find_by_idempotency_key ───────────────────────────────────────────

async def test_save_then_find_by_idempotency_key(repo, db_session):
    n = _make(NotificationStatus.PENDING, idempotency_key="k1", caller="identity-service")
    await repo.save(n)
    await db_session.flush()

    found = await repo.find_by_idempotency_key("identity-service", "k1")
    assert found is not None
    assert found.notification_id == n.notification_id
    assert found.idempotency_key == "k1"
    assert found.caller_service_id == "identity-service"


async def test_find_by_idempotency_key_not_found(repo):
    assert await repo.find_by_idempotency_key("identity-service", "missing") is None


async def test_idempotency_key_scoped_by_caller(repo, db_session):
    await repo.save(_make(NotificationStatus.SENT, idempotency_key="same", caller="a"))
    await repo.save(_make(NotificationStatus.SENT, idempotency_key="same", caller="b"))
    await db_session.flush()

    a = await repo.find_by_idempotency_key("a", "same")
    b = await repo.find_by_idempotency_key("b", "same")
    assert a is not None and b is not None
    assert a.notification_id != b.notification_id


async def test_unknown_caller_uses_empty_bucket(repo, db_session):
    # caller=None lưu thành '' → tra với None vẫn thấy.
    await repo.save(_make(NotificationStatus.SENT, idempotency_key="k", caller=None))
    await db_session.flush()
    found = await repo.find_by_idempotency_key(None, "k")
    assert found is not None
    assert found.caller_service_id is None


async def test_save_upserts_by_id(repo, db_session):
    nid = IdFactory.generate()
    await repo.save(_make(NotificationStatus.PENDING, idempotency_key="k", notification_id=nid))
    await db_session.flush()
    # cùng id, đổi sang SENT.
    await repo.save(_make(NotificationStatus.SENT, idempotency_key="k", notification_id=nid, sent_at=_NOW))
    await db_session.flush()

    found = await repo.find_by_idempotency_key(None, "k")
    assert found.status == NotificationStatus.SENT
    assert found.sent_at is not None


# ── find_due_for_retry ───────────────────────────────────────────────────────

async def test_find_due_includes_pending_and_due_failed(repo, db_session):
    pending = _make(NotificationStatus.PENDING, idempotency_key="p")  # next_retry_at None
    due_failed = _make(
        NotificationStatus.FAILED, idempotency_key="f",
        next_retry_at=_NOW - timedelta(minutes=1),
    )
    await repo.save(pending)
    await repo.save(due_failed)
    await db_session.flush()

    due = await repo.find_due_for_retry(_NOW, limit=10)
    ids = {n.notification_id for n in due}
    assert pending.notification_id in ids
    assert due_failed.notification_id in ids


async def test_find_due_excludes_future_sent_dead(repo, db_session):
    future_failed = _make(
        NotificationStatus.FAILED, idempotency_key="ff",
        next_retry_at=_NOW + timedelta(hours=1),
    )
    sent = _make(NotificationStatus.SENT, idempotency_key="s", sent_at=_NOW)
    dead = _make(NotificationStatus.DEAD_LETTER, idempotency_key="d")
    await repo.save(future_failed)
    await repo.save(sent)
    await repo.save(dead)
    await db_session.flush()

    due = await repo.find_due_for_retry(_NOW, limit=10)
    assert due == []


async def test_find_due_orders_by_created_at_and_respects_limit(repo, db_session):
    older = _make(NotificationStatus.PENDING, idempotency_key="o", created_at=_NOW - timedelta(hours=2))
    newer = _make(NotificationStatus.PENDING, idempotency_key="n", created_at=_NOW - timedelta(hours=1))
    await repo.save(newer)
    await repo.save(older)
    await db_session.flush()

    due = await repo.find_due_for_retry(_NOW, limit=1)
    assert len(due) == 1
    assert due[0].notification_id == older.notification_id


# ── delete_old ───────────────────────────────────────────────────────────────

async def test_delete_old_removes_sent_and_dead_keeps_others(repo, db_session):
    old_sent = _make(NotificationStatus.SENT, idempotency_key="os", sent_at=_NOW - timedelta(days=40))
    recent_sent = _make(NotificationStatus.SENT, idempotency_key="rs", sent_at=_NOW - timedelta(days=1))
    old_dead = _make(NotificationStatus.DEAD_LETTER, idempotency_key="od")
    pending = _make(NotificationStatus.PENDING, idempotency_key="p")
    for n in (old_sent, recent_sent, old_dead, pending):
        await repo.save(n)
    await db_session.flush()

    # updated_at do DB quản lý (= lúc insert); ép về quá khứ để mô phỏng dead-letter cũ.
    await db_session.execute(
        update(EmailNotificationEntity)
        .where(EmailNotificationEntity.notification_id == old_dead.notification_id.to_bytes())
        .values(updated_at=_NOW - timedelta(days=100))
    )
    await db_session.flush()

    removed = await repo.delete_old(
        sent_before=_NOW - timedelta(days=30),
        dead_letter_before=_NOW - timedelta(days=90),
    )
    await db_session.flush()

    assert removed == 2  # old_sent + old_dead
    # recent_sent và pending còn lại.
    assert await repo.find_by_idempotency_key(None, "rs") is not None
    assert await repo.find_by_idempotency_key(None, "p") is not None
    assert await repo.find_by_idempotency_key(None, "os") is None
    assert await repo.find_by_idempotency_key(None, "od") is None
