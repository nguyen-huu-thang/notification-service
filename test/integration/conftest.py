"""
Integration test fixtures cho notification-service.

DB: SQLite in-memory (aiosqlite) + SQLAlchemy async. Mỗi test một engine mới nên
schema sạch, không cần rollback thủ công. Mirror cách data-service dựng repo test.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from xime.starters.sqlalchemy import Base

# Import entity để bảng được đăng ký vào Base.metadata trước create_all.
import app.infrastructure.persistence.entity.EmailNotificationEntity  # noqa: F401


@pytest_asyncio.fixture
async def _engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncSession:
    async_session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


class FakeSessionFactory:
    """Adapts AsyncSession to the AsyncSessionFactory interface used by repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def current(self) -> AsyncSession:
        return self._session
