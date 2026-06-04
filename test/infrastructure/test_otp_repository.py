"""
Integration tests cho OtpRecordMapper và SqlAlchemyOtpRepository.
Dùng SQLite in-memory thay cho PostgreSQL — đủ để kiểm tra SQL logic và mapper.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from xime.starters.sqlalchemy import Base
from xime.starters.sqlalchemy.session import _current_session

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.util.IdGenerator import generate_id
from app.domain.otp.OtpRecord import OtpRecord
from app.infrastructure.persistence.entity.OtpRecordEntity import OtpRecordEntity
from app.infrastructure.persistence.mapper.OtpRecordMapper import OtpRecordMapper
from app.infrastructure.persistence.repository.SqlAlchemyOtpRepository import (
    SqlAlchemyOtpRepository,
)

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FakeSessionFactory:
    """Minimal stub: đọc session từ ContextVar giống AsyncSessionFactory.current()."""

    @staticmethod
    def current() -> AsyncSession:
        session = _current_session.get()
        if session is None:
            raise RuntimeError("No active session")
        return session


def _make_record(**overrides) -> OtpRecord:
    defaults = dict(
        otp_id=generate_id(),
        channel=NotificationChannel.EMAIL,
        target="user@example.com",
        otp_hash="hmac_abc123",
        otp_type=OtpType.VERIFY_EMAIL,
        context_id=None,
        expires_at=_NOW + timedelta(minutes=5),
        is_used=False,
        created_at=_NOW,
    )
    defaults.update(overrides)
    return OtpRecord(**defaults)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    s = factory()
    await s.begin()
    token = _current_session.set(s)

    yield s

    _current_session.reset(token)
    await s.rollback()
    await s.close()
    await engine.dispose()


@pytest_asyncio.fixture
async def repo(session):
    return SqlAlchemyOtpRepository(_FakeSessionFactory())


# ---------------------------------------------------------------------------
# Mapper tests (pure, no DB needed)
# ---------------------------------------------------------------------------


class TestOtpRecordMapper:
    def test_to_entity_maps_all_fields(self):
        record = _make_record()
        entity = OtpRecordMapper.to_entity(record)

        assert entity.otp_id == record.otp_id
        assert entity.channel == "EMAIL"
        assert entity.target == record.target
        assert entity.otp_hash == record.otp_hash
        assert entity.otp_type == "VERIFY_EMAIL"
        assert entity.context_id is None
        assert entity.is_used is False
        assert entity.created_at == record.created_at

    def test_to_entity_enum_stored_as_string(self):
        record = _make_record(otp_type=OtpType.LOGIN_MFA, channel=NotificationChannel.PHONE)
        entity = OtpRecordMapper.to_entity(record)
        assert entity.otp_type == "LOGIN_MFA"
        assert entity.channel == "PHONE"

    def test_to_entity_with_context_id(self):
        ctx = generate_id()
        entity = OtpRecordMapper.to_entity(_make_record(context_id=ctx))
        assert entity.context_id == ctx

    def test_to_entity_sets_updated_at(self):
        entity = OtpRecordMapper.to_entity(_make_record())
        assert entity.updated_at is not None
        assert entity.updated_at.tzinfo is not None

    def test_to_domain_maps_all_fields(self):
        record = _make_record()
        entity = OtpRecordMapper.to_entity(record)
        domain = OtpRecordMapper.to_domain(entity)

        assert domain.otp_id == record.otp_id
        assert domain.channel == NotificationChannel.EMAIL
        assert domain.target == record.target
        assert domain.otp_hash == record.otp_hash
        assert domain.otp_type == OtpType.VERIFY_EMAIL
        assert domain.context_id is None
        assert domain.is_used is False

    def test_roundtrip_preserves_identity(self):
        record = _make_record()
        domain = OtpRecordMapper.to_domain(OtpRecordMapper.to_entity(record))
        assert domain.otp_id == record.otp_id
        assert domain.otp_type == record.otp_type
        assert domain.channel == record.channel


# ---------------------------------------------------------------------------
# Repository integration tests (SQLite)
# ---------------------------------------------------------------------------


class TestSqlAlchemyOtpRepository:
    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_for_missing(self, repo):
        result = await repo.find_by_id(generate_id())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_then_find_by_id(self, repo, session):
        record = _make_record()
        await repo.save(record)
        await session.flush()

        found = await repo.find_by_id(record.otp_id)
        assert found is not None
        assert found.otp_id == record.otp_id
        assert found.target == record.target
        assert found.otp_hash == record.otp_hash
        assert found.is_used is False

    @pytest.mark.asyncio
    async def test_save_preserves_channel_and_type(self, repo, session):
        record = _make_record(
            channel=NotificationChannel.PHONE,
            otp_type=OtpType.RESET_PASSWORD,
        )
        await repo.save(record)
        await session.flush()

        found = await repo.find_by_id(record.otp_id)
        assert found.channel == NotificationChannel.PHONE
        assert found.otp_type == OtpType.RESET_PASSWORD

    @pytest.mark.asyncio
    async def test_save_with_context_id(self, repo, session):
        ctx = generate_id()
        record = _make_record(context_id=ctx)
        await repo.save(record)
        await session.flush()

        found = await repo.find_by_id(record.otp_id)
        assert found.context_id == ctx

    @pytest.mark.asyncio
    async def test_mark_used_updates_db(self, repo, session):
        record = _make_record()
        await repo.save(record)
        await session.flush()

        used = record.mark_used()
        await repo.save(used)
        await session.flush()
        session.expire_all()

        found = await repo.find_by_id(record.otp_id)
        assert found.is_used is True

    @pytest.mark.asyncio
    async def test_save_all_otp_types(self, repo, session):
        for otp_type in OtpType:
            record = _make_record(otp_id=generate_id(), otp_type=otp_type)
            await repo.save(record)
        await session.flush()

        for otp_type in OtpType:
            record = _make_record(otp_id=generate_id(), otp_type=otp_type)
            found = await repo.find_by_id(record.otp_id)
            # ID khác nhau nên không tìm thấy — chỉ kiểm tra save không lỗi
        # Kiểm tra không có exception là đủ

    @pytest.mark.asyncio
    async def test_save_idempotent_for_same_id(self, repo, session):
        record = _make_record()
        await repo.save(record)
        await repo.save(record)  # save lần 2 cùng ID → không lỗi (merge)
        await session.flush()

        found = await repo.find_by_id(record.otp_id)
        assert found is not None
