"""Replay status split and games cleanup.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-14

- Replays: drop status; add status_observer, status_converter, observer_failed_at, converter_failed_at.
- Games: drop status, failed_reason.
- Drop conversion_failures if exists.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Replays: drop status, add new columns ─────────────────────────────────
    op.add_column("replays", sa.Column("status_observer", sa.String(32), nullable=True))
    op.add_column("replays", sa.Column("status_converter", sa.String(32), nullable=True))
    op.add_column("replays", sa.Column("observer_failed_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("replays", sa.Column("converter_failed_at", sa.DateTime(timezone=False), nullable=True))

    # Migrate existing data: set status_converter from old status so we don't lose state
    op.execute(
        """
        UPDATE replays SET status_converter = status, status_observer = status
        WHERE status IS NOT NULL AND status_converter IS NULL
        """
    )
    op.drop_column("replays", "status")

    # ── Games: drop status and failed_reason ───────────────────────────────────
    op.drop_column("games", "status")
    op.drop_column("games", "failed_reason")

    # ── Drop conversion_failures if it exists ─────────────────────────────────
    op.execute("DROP TABLE IF EXISTS conversion_failures")


def downgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS conversion_failures ("
               "game_id INTEGER NOT NULL, player_id INTEGER NOT NULL, "
               "reason TEXT, failed_at TIMESTAMP NOT NULL, "
               "PRIMARY KEY (game_id, player_id))")

    op.add_column("games", sa.Column("status", sa.String(32), nullable=True))
    op.add_column("games", sa.Column("failed_reason", sa.Text(), nullable=True))

    op.add_column("replays", sa.Column("status", sa.String(50), nullable=True))
    op.execute("UPDATE replays SET status = status_converter WHERE status_converter IS NOT NULL")
    op.drop_column("replays", "converter_failed_at")
    op.drop_column("replays", "observer_failed_at")
    op.drop_column("replays", "status_converter")
    op.drop_column("replays", "status_observer")
