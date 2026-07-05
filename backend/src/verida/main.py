"""FastAPI application factory.

Usage
-----
    uvicorn verida.main:app --reload

The module exposes a single ``app`` object created by ``create_app()``.
The startup guard runs before the first request is accepted.
"""

from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from verida.config import get_settings
from verida.api.v1.router import api_v1_router
from verida.infrastructure.security_headers import SecurityHeadersMiddleware

logger = structlog.get_logger(__name__)


def _configure_logging(log_level: str) -> None:
    """Configure structlog for JSON output in all environments."""
    import logging
    import structlog

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level, logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    _configure_logging(settings.log_level)
    logger.info(
        "verida_startup",
        environment=settings.environment,
        version="0.1.0",
    )
    yield
    logger.info("verida_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Calling get_settings() here triggers validation (including the
    DO_NOT_DEPLOY guard) before the app object is returned.
    """
    settings = get_settings()  # raises RuntimeError if guard trips

    app = FastAPI(
        title="VERIDA API",
        description="Proof-of-Human Social Web — API v1",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # ── Security headers (M3) ─────────────────────────────────────────────────
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment=settings.environment,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health endpoint (unauthenticated, used by Docker/K8s probes) ──────────
    @app.get("/health", tags=["observability"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    # ── API v1 ────────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


# Module-level app instance — uvicorn entry point
app = create_app()
