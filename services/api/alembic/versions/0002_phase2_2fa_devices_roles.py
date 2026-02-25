"""Phase 2: 2FA fields, devices table, updated roles enum.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Migrate userrole enum: user/admin → free/pro/admin ───────────────────
    # PostgreSQL requires creating a new type and casting
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('free', 'pro', 'admin')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "  WHEN 'user' THEN 'free'::userrole "
        "  WHEN 'admin' THEN 'admin'::userrole "
        "  ELSE 'free'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'free'")
    op.execute("DROP TYPE userrole_old")

    # ── Add 2FA columns to users ──────────────────────────────────────────────
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("totp_pending_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("email_2fa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("email_2fa_code", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("email_2fa_code_expires_at", sa.DateTime(timezone=True), nullable=True))

    # ── Create devices table ──────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("device_info", sa.Text(), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"])
    op.create_index(op.f("ix_devices_user_id"), "devices", ["user_id"])
    op.create_index(op.f("ix_devices_token_hash"), "devices", ["token_hash"], unique=True)


def downgrade() -> None:
    # ── Drop devices table ────────────────────────────────────────────────────
    op.drop_index(op.f("ix_devices_token_hash"), table_name="devices")
    op.drop_index(op.f("ix_devices_user_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_id"), table_name="devices")
    op.drop_table("devices")

    # ── Remove 2FA columns ────────────────────────────────────────────────────
    op.drop_column("users", "email_2fa_code_expires_at")
    op.drop_column("users", "email_2fa_code")
    op.drop_column("users", "email_2fa_enabled")
    op.drop_column("users", "totp_pending_secret")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")

    # ── Revert userrole enum ──────────────────────────────────────────────────
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('user', 'admin')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "  WHEN 'admin' THEN 'admin'::userrole "
        "  ELSE 'user'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'")
    op.execute("DROP TYPE userrole_old")
