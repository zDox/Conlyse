from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.recording_list import RecordingListAddRequest, RecordingListItem
from app.services import recording_list as recording_list_service

router = APIRouter(prefix="/recording-list", tags=["recording-list"])


@router.get("", response_model=list[RecordingListItem])
async def list_recording_list(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RecordingListItem]:
    rows = await recording_list_service.get_user_recording_list(db, user)
    return [
        RecordingListItem(
            game_id=game.game_id,
            scenario_id=game.scenario_id,
            created_at=entry.created_at,
        )
        for entry, game in rows
    ]


@router.post("", response_model=RecordingListItem, status_code=status.HTTP_201_CREATED)
async def add_to_recording_list(
    data: RecordingListAddRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecordingListItem:
    try:
        entry, game = await recording_list_service.add_game_to_recording_list(db, user, data.game_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return RecordingListItem(
        game_id=game.game_id,
        scenario_id=game.scenario_id,
        created_at=entry.created_at,
    )


@router.delete("/{game_id}", status_code=status.HTTP_200_OK, response_class=Response)
async def remove_from_recording_list(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await recording_list_service.remove_game_from_recording_list(db, user, game_id)

