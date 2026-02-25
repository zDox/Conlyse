from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.subscription import SubscriptionStatusResponse

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    user: User = Depends(get_current_user),
) -> SubscriptionStatusResponse:
    """Return the current user's subscription tier."""
    return SubscriptionStatusResponse(
        tier=user.role, is_pro=user.role in (UserRole.pro, UserRole.admin)
    )
