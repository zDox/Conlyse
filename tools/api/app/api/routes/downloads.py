from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.downloads import PresignedURLResponse
from app.services import downloads as dl_service

router = APIRouter(prefix="/downloads", tags=["downloads"])

# Any authenticated user (free, pro, admin) can download binaries
_any_user = get_current_user
# Pro and admin can download replays / analyses
_require_pro = require_role(UserRole.pro, UserRole.admin)


@router.get("/binary/{platform}", response_model=PresignedURLResponse)
async def download_binary(
    platform: str,
    _: User = Depends(_any_user),
) -> PresignedURLResponse:
    """Return a pre-signed S3 URL for the Conlyse binary (windows / macos / linux)."""
    try:
        url = await dl_service.get_binary_url(platform)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return PresignedURLResponse(url=url, expires_in=settings.MINIO_PRESIGN_EXPIRY)


@router.get("/replay/{game_id}/{player_id}", response_model=PresignedURLResponse)
async def download_replay(
    game_id: str,
    player_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_pro),
) -> PresignedURLResponse:
    """Return a pre-signed S3 URL for a replay file. Requires pro or admin role."""
    try:
        url = await dl_service.get_replay_url(db, game_id, player_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return PresignedURLResponse(url=url, expires_in=settings.MINIO_PRESIGN_EXPIRY)


@router.get("/analysis/{game_id}/{player_id}", response_model=PresignedURLResponse)
async def download_analysis(
    game_id: str,
    player_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_require_pro),
) -> PresignedURLResponse:
    """Return a pre-signed S3 URL for a replay analysis file. Requires pro or admin role."""
    try:
        url = await dl_service.get_analysis_url(db, game_id, player_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return PresignedURLResponse(url=url, expires_in=settings.MINIO_PRESIGN_EXPIRY)


@router.get("/static-map-data/{map_id}", response_model=PresignedURLResponse)
async def download_static_map(
    map_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_any_user),
) -> PresignedURLResponse:
    """Return a pre-signed S3 URL for static map data."""
    try:
        url = await dl_service.get_static_map_url(db, map_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return PresignedURLResponse(url=url, expires_in=settings.MINIO_PRESIGN_EXPIRY)

