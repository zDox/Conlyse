from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import UserRole
from app.schemas.admin import (
    PasswordResetRequest,
    RoleUpdateRequest,
    SubscriptionUpdateRequest,
)
from app.schemas.auth import UserResponse
from app.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin"])

_require_admin = require_role(UserRole.admin)


class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> PaginatedUsersResponse:
    """List all users (paginated). Admin only."""
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination parameters"
        )
    users, total = await admin_service.list_users(db, page, page_size)
    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> UserResponse:
    """Get details of a specific user. Admin only."""
    try:
        user = await admin_service.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_role(
    user_id: int,
    data: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> UserResponse:
    """Assign or change a user's role. Admin only."""
    try:
        user = await admin_service.update_user_role(db, user_id, data.role)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/subscription", response_model=UserResponse)
async def update_subscription(
    user_id: int,
    data: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> UserResponse:
    """Set a user's subscription tier (free / pro). Admin only."""
    try:
        user = await admin_service.update_user_subscription(db, user_id, data.tier)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> UserResponse:
    """Disable (ban) a user account. Admin only."""
    try:
        user = await admin_service.ban_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return UserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def reset_password(
    user_id: int,
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> None:
    """Reset a user's password. Admin only."""
    try:
        await admin_service.reset_user_password(db, user_id, data.new_password)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/users/{user_id}/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def revoke_device(
    user_id: int,
    device_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(_require_admin),
) -> None:
    """Force-logout a specific device for any user. Admin only."""
    try:
        await admin_service.revoke_user_device(db, user_id, device_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
