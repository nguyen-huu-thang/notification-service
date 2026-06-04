from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from xime.starters.sqlalchemy import Base, TimestampMixin


class OtpRecordEntity(TimestampMixin, Base):
    __tablename__ = "otp_records"

    otp_id: Mapped[bytes] = mapped_column(LargeBinary(24), primary_key=True)
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[bytes | None] = mapped_column(LargeBinary(24), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_otp_target_type_used", "target", "otp_type", "is_used"),
        Index("ix_otp_expires", "expires_at"),
    )
