from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, expires_delta: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, device_id: int | None = None) -> str:
    """Create a short-lived JWT access token, optionally bound to a device."""
    extra: dict[str, Any] = {"type": "access"}
    if device_id is not None:
        extra["device_id"] = device_id
    return _create_token(
        subject,
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra,
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        subject,
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        {"type": "refresh"},
    )


def create_2fa_pending_token(subject: str) -> str:
    """Create a short-lived token that indicates password auth passed but 2FA is still required."""
    return _create_token(
        subject,
        timedelta(minutes=10),
        {"type": "2fa_pending"},
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_device_token() -> str:
    """Generate a cryptographically random opaque device token."""
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    """Return the SHA-256 hex digest of *token* for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()
