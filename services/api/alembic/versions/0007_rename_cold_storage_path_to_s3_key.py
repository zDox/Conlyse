"""Rename replays.cold_storage_path to s3_key and normalize values.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-03
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column to s3_key to reflect that we store only the S3 object key.
    op.alter_column("replays", "cold_storage_path", new_column_name="s3_key")

    # Normalize existing values: strip any leading "s3://<bucket>/" prefix so only the key remains.
    # This uses a generic pattern that works for Postgres; other backends used in tests
    # create their own schema (see tests fixtures) and do not run migrations.
    op.execute(
        """
        UPDATE replays
        SET s3_key = regexp_replace(s3_key, '^s3://[^/]+/', '')
        WHERE s3_key LIKE 's3://%';
        """
    )


def downgrade() -> None:
    # Best-effort downgrade: just rename the column back. We do not re-introduce the s3:// prefix.
    op.alter_column("replays", "s3_key", new_column_name="cold_storage_path")

