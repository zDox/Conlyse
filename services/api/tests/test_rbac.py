"""Unit tests for RBAC / permission checks.

Verifies that endpoints correctly enforce role-based access control:
- Unauthenticated requests are rejected (401)
- Authenticated free-tier users are rejected from pro/admin endpoints (403)
- Authenticated pro-tier users can access pro endpoints
- Authenticated admin users can access admin endpoints
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Admin-only endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_list_users_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 422  # missing Authorization header


@pytest.mark.asyncio
async def test_admin_list_users_free_forbidden(client: AsyncClient, free_user: User) -> None:
    response = await client.get("/api/v1/admin/users", headers=auth_headers(free_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_pro_forbidden(client: AsyncClient, pro_user: User) -> None:
    response = await client.get("/api/v1/admin/users", headers=auth_headers(pro_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_admin_allowed(client: AsyncClient, admin_user: User) -> None:
    response = await client.get("/api/v1/admin/users", headers=auth_headers(admin_user))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_get_user_admin_allowed(client: AsyncClient, admin_user: User) -> None:
    response = await client.get(
        f"/api/v1/admin/users/{admin_user.id}", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    assert response.json()["id"] == admin_user.id


@pytest.mark.asyncio
async def test_admin_get_nonexistent_user(client: AsyncClient, admin_user: User) -> None:
    response = await client.get(
        "/api/v1/admin/users/99999", headers=auth_headers(admin_user)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_update_role(
    client: AsyncClient, admin_user: User, free_user: User
) -> None:
    response = await client.patch(
        f"/api/v1/admin/users/{free_user.id}/role",
        json={"role": "pro"},
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "pro"


@pytest.mark.asyncio
async def test_admin_ban_user(
    client: AsyncClient, admin_user: User, free_user: User
) -> None:
    response = await client.post(
        f"/api/v1/admin/users/{free_user.id}/ban", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_reset_password(
    client: AsyncClient, admin_user: User, free_user: User
) -> None:
    response = await client.post(
        f"/api/v1/admin/users/{free_user.id}/reset-password",
        json={"new_password": "newpassword123"},
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Download endpoint RBAC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_analysis_free_forbidden(
    client: AsyncClient, free_user: User
) -> None:
    """Free users cannot access analysis downloads (pro/admin only)."""
    response = await client.get(
        "/api/v1/downloads/analysis/game1/player1",
        headers=auth_headers(free_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_download_analysis_pro_allowed(
    client: AsyncClient, pro_user: User
) -> None:
    """Pro users can reach the analysis endpoint (will 404 since no DB row, not 403)."""
    response = await client.get(
        "/api/v1/downloads/analysis/game1/player1",
        headers=auth_headers(pro_user),
    )
    # 404 means RBAC passed; 403 would mean it was blocked
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_analysis_admin_allowed(
    client: AsyncClient, admin_user: User
) -> None:
    response = await client.get(
        "/api/v1/downloads/analysis/game1/player1",
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 404
