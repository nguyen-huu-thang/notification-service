"""add email_notifications outbox table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # email_notifications — outbox: lưu mọi email để gửi/retry/audit      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "email_notifications",
        sa.Column("notification_id",   sa.LargeBinary(24),         nullable=False),
        sa.Column("caller_service_id", sa.String(100),             nullable=False, server_default=""),
        sa.Column("idempotency_key",   sa.String(255),             nullable=True),
        sa.Column("recipient",         sa.String(320),             nullable=False),
        sa.Column("subject",           sa.String(1000),            nullable=False),
        sa.Column("body",              sa.Text(),                  nullable=False),
        sa.Column("channel",           sa.String(20),              nullable=False),
        sa.Column("status",            sa.String(20),              nullable=False),
        sa.Column("attempts",          sa.Integer(),               nullable=False, server_default="0"),
        sa.Column("next_retry_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code",   sa.String(20),              nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at",           sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("notification_id"),
        sa.UniqueConstraint(
            "caller_service_id",
            "idempotency_key",
            name="uq_email_notifications_idempotency",
        ),
    )
    op.create_index(
        "ix_email_notifications_idempotency_key",
        "email_notifications",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_email_notifications_status",
        "email_notifications",
        ["status"],
    )
    op.create_index(
        "ix_email_notifications_next_retry_at",
        "email_notifications",
        ["next_retry_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_notifications_next_retry_at", table_name="email_notifications")
    op.drop_index("ix_email_notifications_status", table_name="email_notifications")
    op.drop_index("ix_email_notifications_idempotency_key", table_name="email_notifications")
    op.drop_table("email_notifications")
