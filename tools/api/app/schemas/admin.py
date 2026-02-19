from __future__ import annotations

from pydantic import BaseModel

from app.models.user import UserRole


class RoleUpdateRequest(BaseModel):
    role: UserRole


class PasswordResetRequest(BaseModel):
    new_password: str
