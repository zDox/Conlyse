from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.replay_library import ReplayLibraryAddRequest, ReplayLibraryItem
from app.services import replay_library as replay_library_service

router = APIRouter(prefix="/replay-library", tags=["replay-library"])


@router.get("", response_model=list[ReplayLibraryItem])
async def list_replay_library(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ReplayLibraryItem]:
    rows = await replay_library_service.get_user_replay_library(db, user)
    return [
        ReplayLibraryItem(
            game_id=game.game_id,
            scenario_id=game.scenario_id,
            created_at=entry.created_at,
        )
        for entry, game in rows
    ]


@router.post("", response_model=ReplayLibraryItem, status_code=status.HTTP_201_CREATED)
async def add_to_replay_library(
    data: ReplayLibraryAddRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReplayLibraryItem:
    try:
        entry, game = await replay_library_service.add_game_to_replay_library(db, user, data.game_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return ReplayLibraryItem(
        game_id=game.game_id,
        scenario_id=game.scenario_id,
        created_at=entry.created_at,
    )

