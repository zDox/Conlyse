from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

import jwt
import pyotp
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_2fa_pending_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_device_token,
    hash_device_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.device import Device
from app.models.session import Session
from app.models.user import User, UserRole
from app.schemas.auth import (
    DeviceResponse,
    LoginRequest,
    TokenResponse,
    TwoFAPendingResponse,
    UserCreate,
)


async def register_user(db: AsyncSession, data: UserCreate) -> tuple[User, str | None]:
    """Create a new user account.  Raises ValueError on duplicate email/username.

    If ``settings.EMAIL_VERIFICATION_ENABLED`` is True the account is created
    with ``is_email_verified=False`` and a verification code is stored.  The
    caller is responsible for actually sending the code via
    :func:`app.services.email.send_verification_email`.  Returns the new User
    and the verification code (or ``None`` when verification is disabled).
    """
    existing = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if existing.scalars().first():
        raise ValueError("A user with that email or username already exists")

    is_verified = not settings.EMAIL_VERIFICATION_ENABLED
    verification_code: str | None = None
    verification_expires: datetime | None = None

    if settings.EMAIL_VERIFICATION_ENABLED:
        verification_code = _random_code()
        verification_expires = datetime.now(timezone.utc) + timedelta(
            seconds=settings.EMAIL_VERIFICATION_CODE_EXPIRE_SECONDS
        )

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        role=UserRole.free,
        is_active=True,
        is_email_verified=is_verified,
        email_verification_code=verification_code,
        email_verification_code_expires_at=verification_expires,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, verification_code


async def authenticate_user(
    db: AsyncSession,
    data: LoginRequest,
) -> TokenResponse | TwoFAPendingResponse:
    """Validate credentials; if 2FA is enabled return a pending token, else issue JWT pair."""
    result = await db.execute(select(User).where(User.username == data.username))
    user: User | None = result.scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise ValueError("Invalid username or password")
    if not user.is_active:
        raise ValueError("Account is disabled")

    if user.totp_enabled or user.email_2fa_enabled:
        pending = create_2fa_pending_token(str(user.id))
        return TwoFAPendingResponse(two_fa_pending_token=pending)

    return await _issue_tokens_and_device(db, user, data.device_name, data.device_info)


async def complete_2fa_login(
    db: AsyncSession,
    pending_token: str,
    code: str,
    device_name: str = "",
    device_info: str | None = None,
) -> TokenResponse:
    """Verify 2FA code from a pending token and issue the final JWT pair."""
    try:
        payload = decode_token(pending_token)
    except jwt.PyJWTError:
        raise ValueError("Invalid or expired 2FA pending token")

    if payload.get("type") != "2fa_pending":
        raise ValueError("Token is not a 2FA pending token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalars().first()
    if not user or not user.is_active:
        raise ValueError("User not found or disabled")

    # Prefer TOTP if enabled, fall back to email 2FA
    if user.totp_enabled:
        if not user.totp_secret:
            raise ValueError("TOTP not configured")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid TOTP code")
    elif user.email_2fa_enabled:
        now = datetime.now(timezone.utc)
        if (
            user.email_2fa_code != code
            or user.email_2fa_code_expires_at is None
            or user.email_2fa_code_expires_at < now
        ):
            raise ValueError("Invalid or expired email 2FA code")
        user.email_2fa_code = None
        user.email_2fa_code_expires_at = None
    else:
        raise ValueError("No 2FA method configured")

    await db.commit()
    return await _issue_tokens_and_device(db, user, device_name, device_info)


async def _issue_tokens_and_device(
    db: AsyncSession,
    user: User,
    device_name: str = "",
    device_info: str | None = None,
) -> TokenResponse:
    """Create/replace a device record and issue JWT pair."""
    # Enforce max concurrent devices – remove oldest if limit exceeded
    existing_q = await db.execute(
        select(Device)
        .where(Device.user_id == user.id)
        .order_by(Device.created_at.asc())
    )
    existing_devices = list(existing_q.scalars().all())
    while len(existing_devices) >= settings.MAX_DEVICES_PER_USER:
        oldest = existing_devices.pop(0)
        await db.delete(oldest)

    raw_token = generate_device_token()
    token_hash = hash_device_token(raw_token)

    device = Device(
        user_id=user.id,
        device_name=device_name or "unknown",
        device_info=device_info,
        token_hash=token_hash,
        last_active=datetime.now(timezone.utc),
    )
    db.add(device)
    await db.flush()  # get device.id

    access = create_access_token(str(user.id), device_id=device.id)
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


# ── TOTP 2FA ─────────────────────────────────────────────────────────────────

async def totp_enroll(db: AsyncSession, user: User) -> str:
    """Generate a new TOTP secret for the user (pending confirmation).
    Returns the provisioning URI for QR-code generation."""
    secret = pyotp.random_base32()
    user.totp_pending_secret = secret
    await db.commit()
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user.email, issuer_name="Conlyse")


async def totp_verify_enroll(db: AsyncSession, user: User, code: str) -> None:
    """Verify TOTP code and activate TOTP for the user.  Raises ValueError on failure."""
    if not user.totp_pending_secret:
        raise ValueError("No TOTP enrollment in progress")
    totp = pyotp.TOTP(user.totp_pending_secret)
    if not totp.verify(code, valid_window=1):
        raise ValueError("Invalid TOTP code")
    user.totp_secret = user.totp_pending_secret
    user.totp_pending_secret = None
    user.totp_enabled = True
    await db.commit()


async def totp_disable(db: AsyncSession, user: User) -> None:
    """Disable TOTP for the user."""
    user.totp_secret = None
    user.totp_pending_secret = None
    user.totp_enabled = False
    await db.commit()


# ── Email 2FA ─────────────────────────────────────────────────────────────────

def _random_code(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


async def email_2fa_send(db: AsyncSession, user: User) -> str:
    """Generate and store an email 2FA code; return the code for sending."""
    code = _random_code()
    user.email_2fa_code = code
    user.email_2fa_code_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.EMAIL_2FA_CODE_EXPIRE_SECONDS
    )
    user.email_2fa_enabled = True
    await db.commit()
    return code


async def email_2fa_verify(db: AsyncSession, user: User, code: str) -> None:
    """Verify an email 2FA code.  Raises ValueError on failure."""
    now = datetime.now(timezone.utc)
    if (
        user.email_2fa_code != code
        or user.email_2fa_code_expires_at is None
        or user.email_2fa_code_expires_at < now
    ):
        raise ValueError("Invalid or expired email 2FA code")
    user.email_2fa_code = None
    user.email_2fa_code_expires_at = None
    await db.commit()


# ── Device management ─────────────────────────────────────────────────────────

async def list_devices(db: AsyncSession, user: User) -> list[Device]:
    result = await db.execute(
        select(Device).where(Device.user_id == user.id).order_by(Device.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_device(db: AsyncSession, user: User, device_id: int) -> None:
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device: Device | None = result.scalars().first()
    if not device:
        raise LookupError("Device not found")
    await db.delete(device)
    await db.commit()


# ── Email verification ────────────────────────────────────────────────────────

async def verify_email(db: AsyncSession, email: str, code: str) -> None:
    """Verify the email-verification code sent at registration.

    Raises ValueError when the code is invalid, expired, or the user is not found.
    """
    result = await db.execute(select(User).where(User.email == email))
    user: User | None = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    if user.is_email_verified:
        return  # already verified – no-op
    now = datetime.now(timezone.utc)
    if (
        user.email_verification_code != code
        or user.email_verification_code_expires_at is None
        or user.email_verification_code_expires_at < now
    ):
        raise ValueError("Invalid or expired verification code")
    user.is_email_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    await db.commit()

