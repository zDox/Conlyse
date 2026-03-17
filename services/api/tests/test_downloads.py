"""Unit tests for download service logic.

These tests exercise the service functions directly using an in-memory
SQLite database and mock the boto3 S3 client to avoid a real MinIO instance.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.binary import Binary
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
# Platform validation
# ---------------------------------------------------------------------------


def test_validate_platform_valid() -> None:
    for p in ("windows", "macos", "linux"):
        dl_service._validate_platform(p)  # should not raise


def test_validate_platform_invalid() -> None:
    with pytest.raises(ValueError, match="Unsupported platform"):
        dl_service._validate_platform("beos")


# ---------------------------------------------------------------------------
# Binary downloads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_binary_url_latest_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(LookupError, match="No binary found"):
        await dl_service.get_binary_url_latest(db_session, "windows")


@pytest.mark.asyncio
async def test_get_binary_url_latest_success(db_session: AsyncSession) -> None:
    binary = Binary(platform="windows", version="1.0.0", s3_key="binaries/windows/1.0.0/app.exe")
    db_session.add(binary)
    await db_session.commit()

    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        version, url = await dl_service.get_binary_url_latest(db_session, "windows")

    assert version == "1.0.0"
    assert url == _FAKE_URL


@pytest.mark.asyncio
async def test_get_binary_url_version_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(LookupError, match="Binary not found"):
        await dl_service.get_binary_url_version(db_session, "linux", "9.9.9")


@pytest.mark.asyncio
async def test_get_binary_url_version_success(db_session: AsyncSession) -> None:
    binary = Binary(platform="linux", version="2.0.0", s3_key="binaries/linux/2.0.0/app")
    db_session.add(binary)
    await db_session.commit()

    with patch("app.services.downloads._s3_client", return_value=_mock_s3_client()):
        url = await dl_service.get_binary_url_version(db_session, "linux", "2.0.0")

    assert url == _FAKE_URL


@pytest.mark.asyncio
async def test_list_binary_versions_empty(db_session: AsyncSession) -> None:
    versions = await dl_service.list_binary_versions(db_session, "macos")
    assert versions == []


@pytest.mark.asyncio
async def test_list_binary_versions_multiple(db_session: AsyncSession) -> None:
    for v in ("1.0.0", "1.1.0", "2.0.0"):
        db_session.add(Binary(platform="macos", version=v, s3_key=f"binaries/macos/{v}/app"))
    await db_session.commit()

    versions = await dl_service.list_binary_versions(db_session, "macos")
    assert set(versions) == {"1.0.0", "1.1.0", "2.0.0"}


@pytest.mark.asyncio
async def test_register_binary_success(db_session: AsyncSession) -> None:
    binary = await dl_service.register_binary(db_session, "windows", "3.0.0", "some/key.exe")
    assert binary.platform == "windows"
    assert binary.version == "3.0.0"


@pytest.mark.asyncio
async def test_register_binary_duplicate(db_session: AsyncSession) -> None:
    await dl_service.register_binary(db_session, "windows", "4.0.0", "some/key.exe")
    with pytest.raises(ValueError, match="already exists"):
        await dl_service.register_binary(db_session, "windows", "4.0.0", "other/key.exe")


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
