"""Unit tests for download service logic.

These tests exercise the service functions directly using an in-memory
SQLite database and mock the boto3 S3 client to avoid a real MinIO instance.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import downloads as dl_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_URL = "https://minio.example.com/presigned/url"


def _mock_s3_client(presigned_url: str = _FAKE_URL) -> MagicMock:
    """Return a mock boto3 S3 client that returns a fixed pre-signed URL."""
    client = MagicMock()
    client.generate_presigned_url.return_value = presigned_url
    return client


# ---------------------------------------------------------------------------
# Replay / analysis / map presigned URLs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_replay_url_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(LookupError, match="Replay not found"):
        await dl_service.get_replay_url(db_session, 1, 1)


@pytest.mark.asyncio
async def test_get_replay_url_success(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "INSERT INTO replays (game_id, player_id, s3_key) "
            "VALUES (:gid, :pid, :path)"
        ),
        {"gid": 1, "pid": 1, "path": "replays/game1/player1/replay.conrp"},
    )
    await db_session.commit()

    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        url = await dl_service.get_replay_url(db_session, 1, 1)

    assert url == _FAKE_URL


@pytest.mark.asyncio
async def test_get_analysis_url_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(LookupError, match="Analysis not found"):
        await dl_service.get_analysis_url(db_session, "game1", "player1")


@pytest.mark.asyncio
async def test_get_analysis_url_success(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "INSERT INTO replays (game_id, player_id, s3_analysis_path) "
            "VALUES (:gid, :pid, :path)"
        ),
        {"gid": 42, "pid": 7, "path": "analysis/game42/player7/analysis.bin"},
    )
    await db_session.commit()

    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        url = await dl_service.get_analysis_url(db_session, 42, 7)

    assert url == _FAKE_URL


@pytest.mark.asyncio
async def test_get_static_map_url_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(LookupError, match="Map data not found"):
        await dl_service.get_static_map_url(db_session, "map42")


@pytest.mark.asyncio
async def test_get_static_map_url_success(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "INSERT INTO maps (map_id, s3_key) "
            "VALUES (:mid, :key)"
        ),
        {"mid": "map42", "key": "maps/map42/static_map.zst"},
    )
    await db_session.commit()

    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        url = await dl_service.get_static_map_url(db_session, "map42")

    assert url == _FAKE_URL


# ---------------------------------------------------------------------------
# Pre-signed URL generation
# ---------------------------------------------------------------------------


def test_generate_presigned_url_success() -> None:
    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        url = dl_service._generate_presigned_url("mybucket", "some/key")
    assert url == _FAKE_URL


def test_generate_presigned_url_s3_error() -> None:
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_client.generate_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "generate_presigned_url"
    )
    with patch("app.services.downloads._s3_client", return_value=mock_client):
        with pytest.raises(ValueError, match="Could not generate pre-signed URL"):
            dl_service._generate_presigned_url("mybucket", "missing/key")
