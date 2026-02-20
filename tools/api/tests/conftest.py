"""Shared pytest fixtures for the Conlyse API test suite.

Uses an in-memory SQLite database (via aiosqlite) so tests run without
a real PostgreSQL instance.  The ``get_db`` FastAPI dependency is
overridden to yield sessions against the test database.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import get_current_user
from app.main import app
from app.models.base import Base
from app.models.user import User, UserRole
from app.core.database import get_db
from app.core.security import hash_password, create_access_token

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create tables in an in-memory SQLite DB and yield the engine."""
    engine = create_async_engine(TEST_DB_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create legacy tables used by server-converter (raw SQL queries in downloads service)
        await conn.exec_driver_sql(
            """CREATE TABLE IF NOT EXISTS replays (
                id INTEGER PRIMARY KEY,
                game_id TEXT,
                player_id TEXT,
                s3_replay_path TEXT,
                s3_analysis_path TEXT
            )"""
        )
        await conn.exec_driver_sql(
            """CREATE TABLE IF NOT EXISTS static_map_data (
                id INTEGER PRIMARY KEY,
                map_id TEXT,
                s3_path TEXT
            )"""
        )
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Yield an AsyncSession bound to the test engine."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """AsyncClient with the FastAPI app; ``get_db`` uses the test DB."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def free_user(db_session: AsyncSession) -> User:
    """A regular (free) active user stored in the test DB."""
    user = User(
        email="free@example.com",
        username="freeuser",
        hashed_password=hash_password("password123"),
        role=UserRole.free,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def pro_user(db_session: AsyncSession) -> User:
    """A pro-tier active user stored in the test DB."""
    user = User(
        email="pro@example.com",
        username="prouser",
        hashed_password=hash_password("password123"),
        role=UserRole.pro,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """An admin active user stored in the test DB."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("password123"),
        role=UserRole.admin,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    """Return an Authorization header dict for *user*."""
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}
