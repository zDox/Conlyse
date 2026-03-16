from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game, RecordingListEntry
from app.models.user import User, UserRole


async def get_user_recording_list(db: AsyncSession, user: User) -> list[tuple[RecordingListEntry, Game]]:
    result = await db.execute(
        select(RecordingListEntry, Game)
        .join(Game, Game.game_id == RecordingListEntry.game_id)
        .where(RecordingListEntry.user_id == user.id)
        .order_by(RecordingListEntry.created_at.desc())
    )
    return list(result.all())


async def add_game_to_recording_list(db: AsyncSession, user: User, game_id: int) -> tuple[RecordingListEntry, Game]:
    game_result = await db.execute(select(Game).where(Game.game_id == game_id))
    game: Game | None = game_result.scalars().first()
    if not game:
        raise LookupError(f"Game {game_id} not found")

    existing_result = await db.execute(
        select(RecordingListEntry).where(
            RecordingListEntry.user_id == user.id, RecordingListEntry.game_id == game_id
        )
    )
    existing: RecordingListEntry | None = existing_result.scalars().first()
    if existing:
        return existing, game

    if user.role == UserRole.free:
        count_result = await db.execute(
            select(func.count()).select_from(RecordingListEntry).where(RecordingListEntry.user_id == user.id)
        )
        count = int(count_result.scalar_one())
        if count >= 2:
            raise PermissionError("Free tier can only have 2 games on the recording list")

    entry = RecordingListEntry(
        user_id=user.id,
        game_id=game_id,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry, game


async def remove_game_from_recording_list(db: AsyncSession, user: User, game_id: int) -> None:
    result = await db.execute(
        select(RecordingListEntry).where(
            RecordingListEntry.user_id == user.id, RecordingListEntry.game_id == game_id
        )
    )
    entry: RecordingListEntry | None = result.scalars().first()
    if not entry:
        return
    await db.delete(entry)
    await db.commit()

