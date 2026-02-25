from __future__ import annotations

from pydantic import BaseModel

from app.models.user import UserRole


class SubscriptionStatusResponse(BaseModel):
    tier: UserRole
    is_pro: bool
