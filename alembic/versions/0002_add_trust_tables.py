"""add trust certificate and verification key tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # trust_certificate — mTLS certificate cho service này               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "trust_certificate",
        sa.Column("certificate_id",   sa.String(100),            nullable=False),
        sa.Column("service_id",       sa.String(100),            nullable=False),
        sa.Column("public_cert",      sa.Text(),                  nullable=False),
        sa.Column("private_key",      sa.Text(),                  nullable=False),  # encrypted
        sa.Column("refresh_token_id", sa.String(100),            nullable=False),
        sa.Column("refresh_token",    sa.Text(),                  nullable=False),  # encrypted
        sa.Column("issued_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at",       sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("certificate_id"),
    )

    # ------------------------------------------------------------------ #
    # trust_verification_key — public keys để verify JWT                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "trust_verification_key",
        sa.Column("key_id",              sa.String(100),            nullable=False),
        sa.Column("verifier_service_id", sa.String(100),            nullable=False),
        sa.Column("public_key",          sa.Text(),                  nullable=False),
        sa.Column("algorithm",           sa.String(20),              nullable=False),
        sa.Column("key_size",            sa.Integer(),               nullable=False, server_default="0"),
        sa.Column("activate_at",         sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at",          sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key_id"),
    )
    op.create_index(
        "ix_trust_verification_key_expires_at",
        "trust_verification_key",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_trust_verification_key_expires_at", table_name="trust_verification_key")
    op.drop_table("trust_verification_key")
    op.drop_table("trust_certificate")
