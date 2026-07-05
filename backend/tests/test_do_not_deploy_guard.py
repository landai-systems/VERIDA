"""Tests for the DO_NOT_DEPLOY guard.

This test file verifies that the application refuses to start in production
mode unless PROD_RELEASE_APPROVED=explicit-human-signoff is set.

These tests are the automated enforcement of a critical safety control.
They must ALWAYS pass; removing or disabling them is a security incident.
"""

from __future__ import annotations

import os
import pytest


class TestDoNotDeployGuard:
    """Verify that the production startup guard works correctly."""

    def test_guard_raises_in_production_without_approval(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The app MUST refuse to start in production without explicit approval."""
        from verida.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida")
        # Deliberately NOT setting PROD_RELEASE_APPROVED

        with pytest.raises(RuntimeError, match="DO_NOT_DEPLOY GUARD TRIGGERED"):
            get_settings()

    def test_guard_raises_with_wrong_approval_value(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Setting any value other than 'explicit-human-signoff' must not bypass the guard."""
        from verida.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida")
        monkeypatch.setenv("PROD_RELEASE_APPROVED", "yes")  # wrong value

        with pytest.raises(RuntimeError, match="DO_NOT_DEPLOY GUARD TRIGGERED"):
            get_settings()

    def test_guard_raises_with_automation_bypass_attempt(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Common bypass attempts must not work."""
        from verida.config import get_settings

        for bad_value in ("true", "1", "approved", "True", "TRUE", "ok", "yes", ""):
            monkeypatch.setenv("ENVIRONMENT", "production")
            monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
            monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost/verida")
            monkeypatch.setenv("PROD_RELEASE_APPROVED", bad_value)
            get_settings.cache_clear()

            with pytest.raises(RuntimeError, match="DO_NOT_DEPLOY GUARD TRIGGERED"):
                get_settings()

    def test_guard_does_not_trigger_in_development(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Development environment must start without PROD_RELEASE_APPROVED."""
        from verida.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida")
        # Deliberately NOT setting PROD_RELEASE_APPROVED

        settings = get_settings()
        assert settings.environment == "development"

    def test_guard_does_not_trigger_in_staging(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Staging environment must start without PROD_RELEASE_APPROVED."""
        from verida.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida")

        settings = get_settings()
        assert settings.environment == "staging"

    def test_guard_approval_value_is_exact(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The exact string 'explicit-human-signoff' must be accepted in production.

        NOTE: This test documents the behaviour but VERIDA CI must never set
        this value.  It exists only to verify the guard logic is correct.
        """
        from verida.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret-key-for-testing-only-32c!")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://verida:verida@localhost:5432/verida")
        monkeypatch.setenv("PROD_RELEASE_APPROVED", "explicit-human-signoff")

        # Should NOT raise
        settings = get_settings()
        assert settings.environment == "production"
        assert settings.prod_release_approved == "explicit-human-signoff"
