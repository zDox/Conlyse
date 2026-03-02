from __future__ import annotations

import io
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.binary import Binary

# Platforms supported for binary downloads
SUPPORTED_PLATFORMS = {"windows", "macos", "linux"}


def _s3_client():
    """Return a boto3 S3 client pointing at MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _generate_presigned_url(bucket: str, key: str) -> str:
    """Generate a pre-signed GET URL for *bucket/key*."""
    client = _s3_client()
    try:
        url: str = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=settings.MINIO_PRESIGN_EXPIRY,
        )
        return url
    except ClientError as exc:
        raise ValueError(f"Could not generate pre-signed URL: {exc}") from exc


def _validate_platform(platform: str) -> None:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(
            f"Unsupported platform '{platform}'. Choose from: {', '.join(sorted(SUPPORTED_PLATFORMS))}"
        )


async def get_binary_url_latest(db: AsyncSession, platform: str) -> tuple[str, str]:
    """Return (version, presigned_url) for the latest binary of *platform*."""
    _validate_platform(platform)
    result = await db.execute(
        select(Binary)
        .where(Binary.platform == platform)
        .order_by(Binary.created_at.desc())
        .limit(1)
    )
    binary: Binary | None = result.scalars().first()
    if not binary:
        raise LookupError(f"No binary found for platform '{platform}'")
    return binary.version, _generate_presigned_url(settings.MINIO_BUCKET_BINARIES, binary.s3_key)


async def get_binary_url_version(db: AsyncSession, platform: str, version: str) -> str:
    """Return a presigned URL for a specific *version* of the binary for *platform*."""
    _validate_platform(platform)
    result = await db.execute(
        select(Binary).where(Binary.platform == platform, Binary.version == version)
    )
    binary: Binary | None = result.scalars().first()
    if not binary:
        raise LookupError(f"Binary not found for platform '{platform}', version '{version}'")
    return _generate_presigned_url(settings.MINIO_BUCKET_BINARIES, binary.s3_key)


async def list_binary_versions(db: AsyncSession, platform: str) -> list[str]:
    """Return a list of all available version strings for *platform*, newest first."""
    _validate_platform(platform)
    result = await db.execute(
        select(Binary.version).where(Binary.platform == platform).order_by(Binary.created_at.desc())
    )
    return list(result.scalars().all())


async def register_binary(db: AsyncSession, platform: str, version: str, s3_key: str) -> Binary:
    """Register a new binary version in the database.  Raises ValueError on duplicate."""
    _validate_platform(platform)
    existing = await db.execute(
        select(Binary).where(Binary.platform == platform, Binary.version == version)
    )
    if existing.scalars().first():
        raise ValueError(f"Binary for platform '{platform}', version '{version}' already exists")
    binary = Binary(platform=platform, version=version, s3_key=s3_key)
    db.add(binary)
    await db.commit()
    await db.refresh(binary)
    return binary


def upload_binary_to_s3(platform: str, version: str, file_data: bytes, filename: str) -> str:
    """Upload binary file data to S3/MinIO and return the resulting S3 key.

    Key convention: ``binaries/{platform}/{version}/conlyse-{platform}-{version}.ext``
    Raises ValueError on S3 error.
    """
    ext = os.path.splitext(filename)[1] if "." in filename else ""
    s3_key = f"binaries/{platform}/{version}/conlyse-{platform}-{version}{ext}"
    client = _s3_client()
    try:
        client.upload_fileobj(
            io.BytesIO(file_data),
            settings.MINIO_BUCKET_BINARIES,
            s3_key,
        )
    except ClientError as exc:
        raise ValueError(f"Could not upload binary to S3: {exc}") from exc
    return s3_key


async def get_replay_url(db: AsyncSession, game_id: int, player_id: int) -> str:
    """Return a pre-signed URL for the replay file of *game_id*/*player_id*."""
    row = await db.execute(
        text("SELECT cold_storage_path FROM replays WHERE game_id = :gid AND player_id = :pid"),
        {"gid": game_id, "pid": player_id},
    )
    record = row.mappings().first()
    if not record:
        raise LookupError(f"Replay not found for game_id={game_id}, player_id={player_id}")
    return _generate_presigned_url(settings.MINIO_BUCKET_REPLAYS, record["cold_storage_path"])


async def get_analysis_url(db: AsyncSession, game_id: str, player_id: str) -> str:
    """Return a pre-signed URL for the analysis file of *game_id*/*player_id*."""
    row = await db.execute(
        text("SELECT s3_analysis_path FROM replays WHERE game_id = :gid AND player_id = :pid"),
        {"gid": game_id, "pid": player_id},
    )
    record = row.mappings().first()
    if not record:
        raise LookupError(f"Analysis not found for game_id={game_id}, player_id={player_id}")
    return _generate_presigned_url(settings.MINIO_BUCKET_REPLAYS, record["s3_analysis_path"])


async def get_static_map_url(db: AsyncSession, map_id: str) -> str:
    """Return a pre-signed URL for static map data for *map_id*."""
    row = await db.execute(
        text("SELECT s3_key FROM maps WHERE map_id = :mid"),
        {"mid": map_id},
    )
    record = row.mappings().first()
    if not record:
        raise LookupError(f"Map data not found for map_id={map_id}")
    return _generate_presigned_url(settings.MINIO_BUCKET_MAPS, record["s3_key"])
