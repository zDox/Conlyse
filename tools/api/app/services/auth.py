from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.session import Session
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    """Create a new user account.  Raises ValueError on duplicate email/username."""
    existing = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if existing.scalars().first():
        raise ValueError("A user with that email or username already exists")

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        role=UserRole.user,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    """Validate credentials and return JWT pair.  Raises ValueError on failure."""
    result = await db.execute(select(User).where(User.username == data.username))
    user: User | None = result.scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise ValueError("Invalid username or password")
    if not user.is_active:
        raise ValueError("Account is disabled")

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))

    session = Session(
        user_id=user.id,
        refresh_token=refresh,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Issue a new JWT pair from a valid refresh token.  Raises ValueError on failure."""
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Token is not a refresh token")

    result = await db.execute(
        select(Session).where(
            Session.refresh_token == refresh_token,
            Session.is_revoked.is_(False),
        )
    )
    session: Session | None = result.scalars().first()
    if not session:
        raise ValueError("Session not found or already revoked")

    # Revoke old session
    session.is_revoked = True

    user_id = payload["sub"]
    access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)

    new_session = Session(
        user_id=int(user_id),
        refresh_token=new_refresh,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=new_refresh)


async def revoke_session(db: AsyncSession, refresh_token: str) -> None:
    """Mark a session as revoked (logout)."""
    result = await db.execute(
        select(Session).where(Session.refresh_token == refresh_token)
    )
    session: Session | None = result.scalars().first()
    if session:
        session.is_revoked = True
        await db.commit()


async def get_current_user(db: AsyncSession, token: str) -> User:
    """Decode access token and return the associated User.  Raises ValueError on failure."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise ValueError("Invalid or expired access token")

    if payload.get("type") != "access":
        raise ValueError("Token is not an access token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    if not user.is_active:
        raise ValueError("Account is disabled")
    return user
