"""Add games and recording_list tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create games table ──────────────────────────────────────────────────────
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("discovered_date", sa.DateTime(timezone=False), nullable=False),
        sa.Column("started_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("failed_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_games_game_id"),
    )
    op.create_index(op.f("ix_games_id"), "games", ["id"])
    op.create_index(op.f("ix_games_game_id"), "games", ["game_id"])

    # ── Create recording_list table ─────────────────────────────────────────────
    op.create_table(
        "recording_list",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "game_id", name="uq_recording_list_user_game"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.game_id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_recording_list_id"), "recording_list", ["id"])
    op.create_index(op.f("ix_recording_list_user_id"), "recording_list", ["user_id"])
    op.create_index(op.f("ix_recording_list_game_id"), "recording_list", ["game_id"])


def downgrade() -> None:
    # ── Drop recording_list table ───────────────────────────────────────────────
    op.drop_index(op.f("ix_recording_list_game_id"), table_name="recording_list")
    op.drop_index(op.f("ix_recording_list_user_id"), table_name="recording_list")
    op.drop_index(op.f("ix_recording_list_id"), table_name="recording_list")
    op.drop_table("recording_list")

    # ── Drop games table ───────────────────────────────────────────────────────
    op.drop_index(op.f("ix_games_game_id"), table_name="games")
    op.drop_index(op.f("ix_games_id"), table_name="games")
    op.drop_table("games")

