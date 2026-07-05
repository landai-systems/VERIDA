"""Application configuration via Pydantic Settings.

All settings are loaded from environment variables (or .env file in dev).
Validation runs at import time — if required vars are missing or invalid,
the process exits with a clear error message before accepting any requests.

DO_NOT_DEPLOY guard
-------------------
If ENVIRONMENT == "production" and PROD_RELEASE_APPROVED != "explicit-human-signoff",
the application refuses to start.  This prevents accidental production deployments
from CI pipelines or developer machines.

Only a human operator who has reviewed the release should set:
    PROD_RELEASE_APPROVED=explicit-human-signoff
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    Every setting is documented with its purpose, required status, and
    expected format.  Secrets must be supplied via environment variables;
    they are never hard-coded.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Runtime environment ────────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"

    # Production release gate — must be set manually by a human operator.
    # Automation must NEVER set this value.
    prod_release_approved: str = ""

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Auth / JWT ─────────────────────────────────────────────────────────────
    secret_key: str  # Required — generate with: openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Comma-separated list; parsed into a list by the validator below.
    cors_origins: list[str] = ["http://localhost:5173"]

    # ── Email ──────────────────────────────────────────────────────────────────
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: EmailStr = "noreply@verida.example.com"  # type: ignore[assignment]

    # ── Observability ──────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Feature flags ──────────────────────────────────────────────────────────
    enable_authenticity_check: bool = True

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept a comma-separated string or a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        """Reject obviously weak secret keys."""
        weak = {"change-me", "secret", "changeme", "change-me-generate-with-openssl-rand-hex-32"}
        if v.lower() in weak or len(v) < 32:
            msg = (
                "SECRET_KEY is too weak or is still the example value.  "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def do_not_deploy_guard(self) -> "Settings":
        """Refuse to start in production unless a human has explicitly signed off.

        This guard exists to prevent accidental production deployments.
        It must NEVER be bypassed by automation.
        """
        if (
            self.environment == "production"
            and self.prod_release_approved != "explicit-human-signoff"
        ):
            raise RuntimeError(
                "\n"
                "╔══════════════════════════════════════════════════════════════════╗\n"
                "║  DO_NOT_DEPLOY GUARD TRIGGERED                                   ║\n"
                "╠══════════════════════════════════════════════════════════════════╣\n"
                "║  ENVIRONMENT=production requires a human operator to set:        ║\n"
                "║    PROD_RELEASE_APPROVED=explicit-human-signoff                  ║\n"
                "║                                                                  ║\n"
                "║  This value must NEVER be set by automation or CI pipelines.     ║\n"
                "║  A human must review and approve the release before deployment.  ║\n"
                "╚══════════════════════════════════════════════════════════════════╝\n"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Using lru_cache means Settings() is only constructed once per process,
    making startup validation run exactly once and keeping dependency
    injection cheap.
    """
    return Settings()
