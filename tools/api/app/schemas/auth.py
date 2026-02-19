from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores/hyphens allowed)")
        if len(v) < 3 or len(v) > 64:
            raise ValueError("Username must be between 3 and 64 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    username: str
    role: UserRole
    is_active: bool
    totp_enabled: bool
    email_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TwoFAPendingResponse(BaseModel):
    """Returned when 2FA is required after password auth."""
    two_fa_required: bool = True
    two_fa_pending_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str
    device_name: str = ""
    device_info: str | None = None


class TwoFALoginRequest(BaseModel):
    two_fa_pending_token: str
    code: str
    device_name: str = ""
    device_info: str | None = None


class TOTPEnrollResponse(BaseModel):
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str


class EmailTwoFAVerifyRequest(BaseModel):
    code: str


class DeviceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    device_name: str
    device_info: str | None
    last_active: datetime
    created_at: datetime

