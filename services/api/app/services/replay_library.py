from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game, ReplayLibraryEntry
from app.models.user import User, UserRole


async def get_user_replay_library(db: AsyncSession, user: User) -> list[tuple[ReplayLibraryEntry, Game]]:
    result = await db.execute(
        select(ReplayLibraryEntry, Game)
        .join(Game, Game.game_id == ReplayLibraryEntry.game_id)
        .where(ReplayLibraryEntry.user_id == user.id)
        .order_by(ReplayLibraryEntry.created_at.desc())
    )
    return list(result.all())


async def add_game_to_replay_library(
    db: AsyncSession,
    user: User,
    game_id: int,
) -> tuple[ReplayLibraryEntry, Game]:
    game_result = await db.execute(select(Game).where(Game.game_id == game_id))
    game: Game | None = game_result.scalars().first()
    if not game:
        raise LookupError(f"Game {game_id} not found")

    # Only allow adding games that have at least one completed/archived replay, unless admin.
    if user.role != UserRole.admin:
        has_completed = await db.execute(
            text(
                """
                SELECT 1 FROM replays
                WHERE game_id = :gid AND status_converter IN ('completed', 'archived')
                LIMIT 1
                """
            ),
            {"gid": game_id},
        )
        if has_completed.scalar() is None:
            raise PermissionError("Only completed games can be added to the replay library")

    existing_result = await db.execute(
        select(ReplayLibraryEntry).where(
            ReplayLibraryEntry.user_id == user.id,
            ReplayLibraryEntry.game_id == game_id,
        )
    )
    existing: ReplayLibraryEntry | None = existing_result.scalars().first()
    if existing:
        return existing, game

    entry = ReplayLibraryEntry(
        user_id=user.id,
        game_id=game_id,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry, game

