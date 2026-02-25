from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    DeviceResponse,
    EmailTwoFAVerifyRequest,
    EmailVerifyRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    TOTPEnrollResponse,
    TOTPVerifyRequest,
    TwoFALoginRequest,
    TwoFAPendingResponse,
    UserCreate,
    UserResponse,
)
from app.services import auth as auth_service
from app.services.email import send_2fa_code, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Register a new user account.

    When email verification is enabled (``EMAIL_VERIFICATION_ENABLED=true``) a
    verification code is sent to the provided address and the account remains
    unverified until ``POST /auth/verify-email`` is called.
    """
    try:
        user, verification_code = await auth_service.register_user(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if settings.EMAIL_VERIFICATION_ENABLED and verification_code:
        try:
            send_verification_email(user.email, verification_code)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return UserResponse.model_validate(user)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def verify_email(data: EmailVerifyRequest, db: AsyncSession = Depends(get_db)) -> None:
    """Verify email address using the code sent at registration."""
    try:
        await auth_service.verify_email(db, data.email, data.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login")
async def login(
    data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse | TwoFAPendingResponse:
    """Authenticate and receive JWT tokens. If 2FA is enabled, returns a pending token."""
    try:
        result = await auth_service.authenticate_user(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return result


@router.post("/2fa/verify", response_model=TokenResponse)
async def two_fa_verify(
    data: TwoFALoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Complete 2FA login by providing the code after password authentication."""
    try:
        tokens = await auth_service.complete_2fa_login(
            db, data.two_fa_pending_token, data.code, data.device_name, data.device_info
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange a refresh token for a new JWT pair."""
    try:
        tokens = await auth_service.refresh_tokens(db, data.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> None:
    """Invalidate a refresh token / session."""
    await auth_service.revoke_session(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(user)


# ── TOTP 2FA ──────────────────────────────────────────────────────────────────


@router.post("/2fa/totp/enroll", response_model=TOTPEnrollResponse)
async def totp_enroll(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TOTPEnrollResponse:
    """Generate a TOTP secret and return the provisioning URI for QR code generation."""
    uri = await auth_service.totp_enroll(db, user)
    return TOTPEnrollResponse(provisioning_uri=uri)


@router.post("/2fa/totp/verify", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def totp_verify_enroll(
    data: TOTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Verify TOTP code to complete enrollment."""
    try:
        await auth_service.totp_verify_enroll(db, user, data.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/2fa/totp/disable", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def totp_disable(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Disable TOTP 2FA for the current user."""
    await auth_service.totp_disable(db, user)


# ── Email 2FA ─────────────────────────────────────────────────────────────────


@router.post("/2fa/email/send", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def email_2fa_send(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Send a verification code to the user's registered email address."""
    code = await auth_service.email_2fa_send(db, user)
    try:
        send_2fa_code(user.email, code)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post("/2fa/email/verify", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def email_2fa_verify(
    data: EmailTwoFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Verify the email 2FA code."""
    try:
        await auth_service.email_2fa_verify(db, user, data.code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Device management ─────────────────────────────────────────────────────────


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DeviceResponse]:
    """List all active devices for the current user."""
    devices = await auth_service.list_devices(db, user)
    return [DeviceResponse.model_validate(d) for d in devices]


@router.delete(
    "/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def revoke_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Revoke (force-logout) a specific device session."""
    try:
        await auth_service.revoke_device(db, user, device_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
