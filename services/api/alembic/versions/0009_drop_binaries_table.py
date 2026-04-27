"""Drop binaries table — binary distribution moved to GitHub Releases.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_binaries_platform_version", "binaries", type_="unique")
    op.drop_index(op.f("ix_binaries_platform"), table_name="binaries")
    op.drop_index(op.f("ix_binaries_id"), table_name="binaries")
    op.drop_table("binaries")


def downgrade() -> None:
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
