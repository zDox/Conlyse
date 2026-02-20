from __future__ import annotations

from pydantic import BaseModel

from app.models.user import UserRole


class RoleUpdateRequest(BaseModel):
    role: UserRole


class PasswordResetRequest(BaseModel):
    new_password: str


class SubscriptionUpdateRequest(BaseModel):
    tier: UserRole


class BinaryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    platform: str
    version: str
    s3_key: str
