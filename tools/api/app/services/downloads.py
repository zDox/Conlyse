from __future__ import annotations

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

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


async def get_binary_url(platform: str) -> str:
    """Return a pre-signed URL for the Conlyse binary for *platform*."""
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform '{platform}'. Choose from: {', '.join(sorted(SUPPORTED_PLATFORMS))}")
    key = f"conlyse-{platform}.zip"
    return _generate_presigned_url(settings.MINIO_BUCKET_BINARIES, key)


async def get_replay_url(db: AsyncSession, game_id: str, player_id: str) -> str:
    """Return a pre-signed URL for the replay file of *game_id*/*player_id*."""
    row = await db.execute(
        text("SELECT s3_replay_path FROM replays WHERE game_id = :gid AND player_id = :pid"),
        {"gid": game_id, "pid": player_id},
    )
    record = row.mappings().first()
    if not record:
        raise LookupError(f"Replay not found for game_id={game_id}, player_id={player_id}")
    return _generate_presigned_url(settings.MINIO_BUCKET_REPLAYS, record["s3_replay_path"])


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
        text("SELECT s3_path FROM static_map_data WHERE map_id = :mid"),
        {"mid": map_id},
    )
    record = row.mappings().first()
    if not record:
        raise LookupError(f"Map data not found for map_id={map_id}")
    return _generate_presigned_url(settings.MINIO_BUCKET_MAPS, record["s3_path"])
