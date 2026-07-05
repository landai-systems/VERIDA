"""API v1 root router — aggregates all sub-routers.

Each sub-module (auth, capture, posts, circles, feed, health) registers its
own APIRouter.  This module includes them all under a single ``api_v1_router``
that is mounted at ``/api/v1`` in ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from verida.api.v1.auth import router as auth_router
from verida.api.v1.capture import router as capture_router
from verida.api.v1.circles import router as circles_router
from verida.api.v1.feed import router as feed_router
from verida.api.v1.posts import router as posts_router

api_v1_router = APIRouter()

# ── Auth ───────────────────────────────────────────────────────────────────────
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Capture flow ───────────────────────────────────────────────────────────────
api_v1_router.include_router(capture_router, prefix="/capture", tags=["capture"])

# ── Posts ──────────────────────────────────────────────────────────────────────
api_v1_router.include_router(posts_router, prefix="/posts", tags=["posts"])

# ── Circles ────────────────────────────────────────────────────────────────────
api_v1_router.include_router(circles_router, prefix="/circles", tags=["circles"])

# ── Feed ───────────────────────────────────────────────────────────────────────
api_v1_router.include_router(feed_router, prefix="/feed", tags=["feed"])

# ── Observability ──────────────────────────────────────────────────────────────
health_router = APIRouter()


@health_router.get("/ping", summary="Lightweight ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


api_v1_router.include_router(health_router, prefix="/health", tags=["observability"])
