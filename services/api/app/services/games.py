from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game


async def list_games(db: AsyncSession) -> list[Game]:
    """Return all games discovered by the observer, ordered by discovered_date desc."""
    result = await db.execute(
        select(Game).order_by(Game.discovered_date.desc())
    )
    return list(result.scalars().all())

