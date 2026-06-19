from sqlalchemy import (
    DateTime,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from xime.starters.sqlalchemy import Base


class EmailNotificationEntity(Base):
    __tablename__ = "email_notifications"

    __table_args__ = (
        # Dedupe theo (caller, idempotency_key). caller rỗng = caller chưa xác định
        # (mọi caller chưa biết gom chung một bucket để vẫn dedupe được theo key).
        UniqueConstraint(
            "caller_service_id",
            "idempotency_key",
            name="uq_email_notifications_idempotency",
        ),
    )

    notification_id: Mapped[bytes] = mapped_column(
        LargeBinary(24),
        primary_key=True,
    )

    # Empty string = unknown caller; never NULL so the unique constraint dedupes.
    # Chuỗi rỗng = caller chưa xác định; không bao giờ NULL để unique constraint dedupe được.
    caller_service_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    recipient: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    next_retry_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    last_error_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # DB-managed; bumped on every UPDATE — used by the retention cleanup job.
    # DB tự quản; tự cập nhật mỗi lần UPDATE — dùng cho job dọn dữ liệu cũ.
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sent_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
