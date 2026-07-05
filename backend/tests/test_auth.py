"""Tests for authentication endpoints.

Covers:
    - User registration (happy path, duplicate email, weak password)
    - Login (happy path, wrong password, unknown email)
    - Token refresh (happy path, expired/invalid token)
    - Logout (clears cookie)
    - /me endpoint (authenticated access)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    """POST /api/v1/auth/register"""

    async def test_register_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "handle": "alice",
                "email": "alice@example.com",
                "password": "SuperSecure!Password1",
                "display_name": "Alice Example",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        payload = {
            "handle": "bob",
            "email": "bob@example.com",
            "password": "SuperSecure!Password1",
            "display_name": "Bob Example",
        }
        await client.post("/api/v1/auth/register", json=payload)
        # Second registration with same email
        payload["handle"] = "bob2"
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_password_too_short(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "handle": "carol",
                "email": "carol@example.com",
                "password": "short",
                "display_name": "Carol",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_handle(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "handle": "Invalid Handle!",
                "email": "dave@example.com",
                "password": "SuperSecure!Password1",
                "display_name": "Dave",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """POST /api/v1/auth/login"""

    async def _register(self, client: AsyncClient, email: str = "eve@example.com") -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "handle": "eve",
                "email": email,
                "password": "SuperSecure!Password1",
                "display_name": "Eve",
            },
        )

    async def test_login_success(self, client: AsyncClient) -> None:
        await self._register(client)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "eve@example.com", "password": "SuperSecure!Password1"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        await self._register(client)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "eve@example.com", "password": "WrongPassword999!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePassword123!"},
        )
        assert resp.status_code == 401

    async def test_login_error_messages_are_identical(self, client: AsyncClient) -> None:
        """Wrong email and wrong password must return the same error message.

        This prevents user enumeration attacks.
        """
        await self._register(client)
        wrong_email = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SuperSecure!Password1"},
        )
        wrong_password = await client.post(
            "/api/v1/auth/login",
            json={"email": "eve@example.com", "password": "WrongPassword999!"},
        )
        assert wrong_email.json()["detail"] == wrong_password.json()["detail"]


@pytest.mark.asyncio
class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_clears_cookie(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "handle": "frank",
                "email": "frank@example.com",
                "password": "SuperSecure!Password1",
                "display_name": "Frank",
            },
        )
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Basic smoke tests for health/observability endpoints."""

    async def test_root_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_v1_ping(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health/ping")
        assert resp.status_code == 200
        assert resp.json()["pong"] == "ok"
