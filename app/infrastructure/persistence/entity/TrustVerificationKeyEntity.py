from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from xime.starters.sqlalchemy import Base


class TrustVerificationKeyEntity(Base):
    __tablename__ = "trust_verification_key"

    key_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    verifier_service_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # PEM public key — no private key for verify-only service
    public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    algorithm: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    key_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    activate_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
