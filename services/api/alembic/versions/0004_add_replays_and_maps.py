"""Add replays and maps tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-26

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create replays table ────────────────────────────────────────────────────
    op.create_table(
        "replays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("replay_name", sa.String(255), nullable=False),
        sa.Column("hot_storage_path", sa.Text(), nullable=True),
        sa.Column("cold_storage_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("recording_start_time", sa.DateTime(timezone=False), nullable=True),
        sa.Column("recording_end_time", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column(
            "response_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("replay_name", name="uq_replays_replay_name"),
        sa.UniqueConstraint("game_id", "player_id", name="uq_replays_game_player"),
    )
    op.create_index(op.f("ix_replays_id"), "replays", ["id"])
    op.create_index(op.f("ix_replays_game_id"), "replays", ["game_id"])
    op.create_index(op.f("ix_replays_player_id"), "replays", ["player_id"])

    # ── Create maps table ──────────────────────────────────────────────────────
    op.create_table(
        "maps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("map_id", sa.String(40), nullable=False),
        sa.Column("version", sa.String(64), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("map_id", name="uq_maps_map_id"),
    )
    op.create_index(op.f("ix_maps_id"), "maps", ["id"])
    op.create_index(op.f("ix_maps_map_id"), "maps", ["map_id"])


def downgrade() -> None:
    # ── Drop maps table ────────────────────────────────────────────────────────
    op.drop_index(op.f("ix_maps_map_id"), table_name="maps")
    op.drop_index(op.f("ix_maps_id"), table_name="maps")
    op.drop_table("maps")

    # ── Drop replays table ─────────────────────────────────────────────────────
    op.drop_index(op.f("ix_replays_player_id"), table_name="replays")
    op.drop_index(op.f("ix_replays_game_id"), table_name="replays")
    op.drop_index(op.f("ix_replays_id"), table_name="replays")
    op.drop_table("replays")

