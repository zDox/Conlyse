"""Unit tests for authentication flows.

Covers: register, login, 2FA (TOTP + email), token refresh, logout,
device management, and the /auth/me endpoint.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "username": "newuser", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["username"] == "newuser"
    assert data["role"] == "free"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "username": "dupuser1", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    # same email, different username
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "username": "dupuser2", "password": "password123"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "username": "sameuser", "password": "password123"},
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "username": "sameuser", "password": "password123"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "username": "shortpw", "password": "abc"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, free_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, free_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "password123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_banned_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user = User(
        email="banned@example.com",
        username="banneduser",
        hashed_password=hash_password("password123"),
        role=UserRole.free,
        is_active=False,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "banneduser", "password": "password123"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, free_user: User) -> None:
    response = await client.get("/api/v1/auth/me", headers=auth_headers(free_user))
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "freeuser"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 422  # missing Authorization header


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh & logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_and_logout(client: AsyncClient, free_user: User) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "password123"},
    )
    tokens = login_resp.json()

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens

    # logout with the new refresh token
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 204


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "notavalidtoken"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# TOTP 2FA
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_totp_enroll_and_login(client: AsyncClient, free_user: User) -> None:
    # Enroll
    enroll_resp = await client.post(
        "/api/v1/auth/2fa/totp/enroll", headers=auth_headers(free_user)
    )
    assert enroll_resp.status_code == 200
    uri = enroll_resp.json()["provisioning_uri"]
    assert "otpauth://" in uri

    # Extract secret from the URI and confirm enrollment
    secret = pyotp.parse_uri(uri).secret
    code = pyotp.TOTP(secret).now()
    verify_resp = await client.post(
        "/api/v1/auth/2fa/totp/verify",
        json={"code": code},
        headers=auth_headers(free_user),
    )
    assert verify_resp.status_code == 204

    # Login should now return a pending token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "password123"},
    )
    assert login_resp.status_code == 200
    pending = login_resp.json()
    assert pending.get("two_fa_required") is True

    # Complete 2FA login
    code2 = pyotp.TOTP(secret).now()
    complete_resp = await client.post(
        "/api/v1/auth/2fa/verify",
        json={"two_fa_pending_token": pending["two_fa_pending_token"], "code": code2},
    )
    assert complete_resp.status_code == 200
    assert "access_token" in complete_resp.json()


@pytest.mark.asyncio
async def test_totp_disable(client: AsyncClient, free_user: User) -> None:
    # Enroll and verify first
    enroll_resp = await client.post(
        "/api/v1/auth/2fa/totp/enroll", headers=auth_headers(free_user)
    )
    uri = enroll_resp.json()["provisioning_uri"]
    secret = pyotp.parse_uri(uri).secret
    code = pyotp.TOTP(secret).now()
    await client.post(
        "/api/v1/auth/2fa/totp/verify",
        json={"code": code},
        headers=auth_headers(free_user),
    )

    # Disable TOTP
    disable_resp = await client.post(
        "/api/v1/auth/2fa/totp/disable", headers=auth_headers(free_user)
    )
    assert disable_resp.status_code == 204

    # Login should now return tokens directly (no 2FA)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "password123"},
    )
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_totp_invalid_code(client: AsyncClient, free_user: User) -> None:
    # Enroll
    enroll_resp = await client.post(
        "/api/v1/auth/2fa/totp/enroll", headers=auth_headers(free_user)
    )
    assert enroll_resp.status_code == 200

    # Wrong code should fail
    verify_resp = await client.post(
        "/api/v1/auth/2fa/totp/verify",
        json={"code": "000000"},
        headers=auth_headers(free_user),
    )
    assert verify_resp.status_code == 400


# ---------------------------------------------------------------------------
# Email 2FA
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_2fa_send_and_verify(
    client: AsyncClient, free_user: User, db_session: AsyncSession
) -> None:
    # Store the code via the service (same session the free_user fixture used)
    from app.services import auth as auth_service

    code = await auth_service.email_2fa_send(db_session, free_user)
    assert len(code) == 6
    assert code.isdigit()

    # Verify the code via the HTTP endpoint
    verify_resp = await client.post(
        "/api/v1/auth/2fa/email/verify",
        json={"code": code},
        headers=auth_headers(free_user),
    )
    assert verify_resp.status_code == 204


@pytest.mark.asyncio
async def test_email_2fa_wrong_code(client: AsyncClient, free_user: User) -> None:
    with patch("app.api.routes.auth.send_2fa_code"):
        await client.post("/api/v1/auth/2fa/email/send", headers=auth_headers(free_user))

    # Provide wrong code
    response = await client.post(
        "/api/v1/auth/2fa/email/verify",
        json={"code": "000000"},
        headers=auth_headers(free_user),
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Device management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_devices(client: AsyncClient, free_user: User) -> None:
    # Create a session/device via login
    await client.post(
        "/api/v1/auth/login",
        json={
            "username": "freeuser",
            "password": "password123",
            "device_name": "test-device",
        },
    )
    response = await client.get("/api/v1/auth/devices", headers=auth_headers(free_user))
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) >= 1
    assert devices[0]["device_name"] == "test-device"


@pytest.mark.asyncio
async def test_revoke_device(client: AsyncClient, free_user: User) -> None:
    await client.post(
        "/api/v1/auth/login",
        json={"username": "freeuser", "password": "password123", "device_name": "dev1"},
    )
    list_resp = await client.get("/api/v1/auth/devices", headers=auth_headers(free_user))
    device_id = list_resp.json()[0]["id"]

    del_resp = await client.delete(
        f"/api/v1/auth/devices/{device_id}", headers=auth_headers(free_user)
    )
    assert del_resp.status_code == 204

    # Device should be gone
    list_resp2 = await client.get("/api/v1/auth/devices", headers=auth_headers(free_user))
    ids = [d["id"] for d in list_resp2.json()]
    assert device_id not in ids


@pytest.mark.asyncio
async def test_revoke_nonexistent_device(client: AsyncClient, free_user: User) -> None:
    response = await client.delete(
        "/api/v1/auth/devices/99999", headers=auth_headers(free_user)
    )
    assert response.status_code == 404
