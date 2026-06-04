"""create otp_records

Revision ID: 0001
Revises:
Create Date: 2026-06-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "otp_records",
        sa.Column("otp_id", sa.LargeBinary(24), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("otp_type", sa.String(50), nullable=False),
        sa.Column("context_id", sa.LargeBinary(24), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("otp_id"),
    )
    op.create_index("ix_otp_target_type_used", "otp_records", ["target", "otp_type", "is_used"])
    op.create_index("ix_otp_expires", "otp_records", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_otp_expires", table_name="otp_records")
    op.drop_index("ix_otp_target_type_used", table_name="otp_records")
    op.drop_table("otp_records")
