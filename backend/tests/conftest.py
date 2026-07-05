"""pytest configuration and shared fixtures.

Test categories:
    unit        — pure domain/application tests, no I/O
    integration — tests against real DB/Redis (via testcontainers)
    e2e         — full HTTP round-trips via httpx.AsyncClient

Run only unit tests in CI fast path:
    pytest -m unit

Run all tests (integration requires Docker):
    pytest
"""

from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ── Environment isolation ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the lru_cache on Settings between tests.

    This allows tests to set different env vars without interfering.
    """
    from verida.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── Application fixture ───────────────────────────────────────────────────────

@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Return a FastAPI test app with safe development settings."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long!")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida_test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("EMAIL_FROM", "noreply@verida.example.com")

    from verida.main import create_app
    return create_app()


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP test client bound to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
