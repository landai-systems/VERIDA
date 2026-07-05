"""API v1 root router — aggregates all sub-routers.

Each sub-module (auth, posts, circles, health) registers its own APIRouter.
This module includes them all under a single ``api_v1_router`` that is
mounted at ``/api/v1`` in ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from verida.api.v1.auth import router as auth_router

api_v1_router = APIRouter()

# ── Auth ───────────────────────────────────────────────────────────────────────
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Posts ──────────────────────────────────────────────────────────────────────
# Placeholder — will be implemented in M2
posts_router = APIRouter()


@posts_router.get("/", summary="List posts (stub)")
async def list_posts() -> dict[str, str]:
    return {"status": "not_yet_implemented", "milestone": "M2"}


api_v1_router.include_router(posts_router, prefix="/posts", tags=["posts"])

# ── Circles ────────────────────────────────────────────────────────────────────
circles_router = APIRouter()


@circles_router.get("/", summary="List circles (stub)")
async def list_circles() -> dict[str, str]:
    return {"status": "not_yet_implemented", "milestone": "M2"}


api_v1_router.include_router(circles_router, prefix="/circles", tags=["circles"])

# ── Observability ──────────────────────────────────────────────────────────────
health_router = APIRouter()


@health_router.get("/ping", summary="Lightweight ping")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


api_v1_router.include_router(health_router, prefix="/health", tags=["observability"])
