from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.user import User, UserRole
from app.services import replay_library as replay_library_service


@pytest.mark.asyncio
async def test_get_user_replay_library_empty(db_session: AsyncSession, free_user: User) -> None:
    rows = await replay_library_service.get_user_replay_library(db_session, free_user)
    assert rows == []


@pytest.mark.asyncio
async def test_add_game_to_replay_library_requires_completed_status(db_session: AsyncSession, free_user: User) -> None:
    game = Game(game_id=1, scenario_id=10)
    db_session.add(game)
    await db_session.commit()
    # No replay with status_converter completed/archived -> add should be denied

    with pytest.raises(PermissionError, match="Only completed games"):
        await replay_library_service.add_game_to_replay_library(db_session, free_user, game_id=1)


@pytest.mark.asyncio
async def test_add_game_to_replay_library_admin_can_add_any_status(
    db_session: AsyncSession,
) -> None:
    admin = User(
        email="admin2@example.com",
        username="admin2",
        hashed_password="x",
        role=UserRole.admin,
        is_active=True,
        is_email_verified=True,
    )
    game = Game(game_id=2, scenario_id=20)
    db_session.add_all([admin, game])
    await db_session.commit()

    entry, loaded_game = await replay_library_service.add_game_to_replay_library(
        db_session, admin, game_id=2
    )

    assert entry.user_id == admin.id
    assert entry.game_id == 2
    assert loaded_game.game_id == 2


@pytest.mark.asyncio
async def test_add_game_to_replay_library_completed_game(
    db_session: AsyncSession,
    free_user: User,
) -> None:
    game = Game(game_id=3, scenario_id=30)
    db_session.add(game)
    await db_session.commit()
    # Replay with status_converter completed so add is allowed
    await db_session.execute(
        text(
            "INSERT INTO replays (game_id, player_id, replay_name, status_converter, created_at, updated_at) "
            "VALUES (3, 0, 'game_3_player_0', 'completed', datetime('now'), datetime('now'))"
        )
    )
    await db_session.commit()

    entry, loaded_game = await replay_library_service.add_game_to_replay_library(
        db_session, free_user, game_id=3
    )

    assert entry.user_id == free_user.id
    assert entry.game_id == 3
    assert loaded_game.game_id == 3

    # Idempotent: calling again should return the same entry, not create a duplicate.
    entry2, loaded_game2 = await replay_library_service.add_game_to_replay_library(
        db_session, free_user, game_id=3
    )
    assert entry2.id == entry.id
    assert loaded_game2.game_id == 3


@pytest.mark.asyncio
async def test_get_user_replay_library_returns_items(
    db_session: AsyncSession,
    free_user: User,
) -> None:
    game = Game(game_id=4, scenario_id=40)
    db_session.add(game)
    await db_session.commit()
    await db_session.execute(
        text(
            "INSERT INTO replays (game_id, player_id, replay_name, status_converter, created_at, updated_at) "
            "VALUES (4, 0, 'game_4_player_0', 'completed', datetime('now'), datetime('now'))"
        )
    )
    await db_session.commit()

    await replay_library_service.add_game_to_replay_library(db_session, free_user, game_id=4)

    rows = await replay_library_service.get_user_replay_library(db_session, free_user)
    assert len(rows) == 1
    entry, loaded_game = rows[0]
    assert entry.user_id == free_user.id
    assert loaded_game.game_id == 4

