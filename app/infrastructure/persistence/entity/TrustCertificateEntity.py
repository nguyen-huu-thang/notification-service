from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from xime.starters.sqlalchemy import Base


class TrustCertificateEntity(Base):
    __tablename__ = "trust_certificate"

    certificate_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    service_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    public_cert: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Encrypted with Fernet before storage
    private_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    refresh_token_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Encrypted with Fernet before storage
    refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    issued_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
