from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.services import auth as auth_service


def _bearer_token(authorization: str = Header(...)) -> str:
    """Extract Bearer token from Authorization header."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return token


async def get_current_user(
    token: str = Depends(_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — decode access token and return the active User."""
    try:
        user = await auth_service.get_current_user(db, token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return user


def require_role(*roles: UserRole):
    """Return a FastAPI dependency that enforces one of the given roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
