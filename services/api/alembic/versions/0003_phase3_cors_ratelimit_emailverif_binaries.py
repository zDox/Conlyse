"""Phase 3: CORS, rate-limiting, email verification, versioned binaries, subscription.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-20

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add email-verification columns to users ───────────────────────────────
    op.add_column("users", sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("email_verification_code", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("email_verification_code_expires_at", sa.DateTime(timezone=True), nullable=True))

    # ── Create binaries table ─────────────────────────────────────────────────
    op.create_table(
        "binaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_binaries_id"), "binaries", ["id"])
    op.create_index(op.f("ix_binaries_platform"), "binaries", ["platform"])
    op.create_unique_constraint("uq_binaries_platform_version", "binaries", ["platform", "version"])


def downgrade() -> None:
    # ── Drop binaries table ───────────────────────────────────────────────────
    op.drop_constraint("uq_binaries_platform_version", "binaries", type_="unique")
    op.drop_index(op.f("ix_binaries_platform"), table_name="binaries")
    op.drop_index(op.f("ix_binaries_id"), table_name="binaries")
    op.drop_table("binaries")

    # ── Remove email-verification columns ─────────────────────────────────────
    op.drop_column("users", "email_verification_code_expires_at")
    op.drop_column("users", "email_verification_code")
    op.drop_column("users", "is_email_verified")
