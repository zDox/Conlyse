"""Add replay_library table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create replay_library table ──────────────────────────────────────────────
    op.create_table(
        "replay_library",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "game_id", name="uq_replay_library_user_game"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.game_id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_replay_library_id"), "replay_library", ["id"])
    op.create_index(op.f("ix_replay_library_user_id"), "replay_library", ["user_id"])
    op.create_index(op.f("ix_replay_library_game_id"), "replay_library", ["game_id"])


def downgrade() -> None:
    # ── Drop replay_library table ────────────────────────────────────────────────
    op.drop_index(op.f("ix_replay_library_game_id"), table_name="replay_library")
    op.drop_index(op.f("ix_replay_library_user_id"), table_name="replay_library")
    op.drop_index(op.f("ix_replay_library_id"), table_name="replay_library")
    op.drop_table("replay_library")

