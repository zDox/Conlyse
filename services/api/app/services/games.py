from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game


async def list_games(db: AsyncSession) -> list[tuple[Game, str]]:
    """Return all games discovered by the observer with computed status from replays.
    Status is taken from replays.status_observer (one row per game, prefer player_id = 0).
    """
    result = await db.execute(
        select(Game).order_by(Game.discovered_date.desc())
    )
    games = list(result.scalars().all())
    if not games:
        return []

    # One row per game: status_observer from replays (prefer player_id = 0)
    status_result = await db.execute(
        text(
            """
            SELECT DISTINCT ON (game_id) game_id, status_observer
            FROM replays
            WHERE status_observer IS NOT NULL
            ORDER BY game_id, player_id
            """
        )
    )
    status_map = {row[0]: (row[1] or "unknown") for row in status_result.all()}

    return [(g, status_map.get(g.game_id, "unknown")) for g in games]

