from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.game import Game
from app.schemas.games import GameItem
from app.services import games as games_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameItem])
async def list_games(
    db: AsyncSession = Depends(get_db),
) -> list[GameItem]:
    rows: list[tuple[Game, str]] = await games_service.list_games(db)
    return [
        GameItem(
            game_id=game.game_id,
            scenario_id=game.scenario_id,
            status=status,
            discovered_date=game.discovered_date,
            started_date=game.started_date,
            completed_date=game.completed_date,
        )
        for game, status in rows
    ]

