"""Feed endpoint — chronological, reciprocity-gated.

GET /api/v1/feed

- Requires authentication.
- Returns posts from today by users in the viewer's circles.
- Reciprocity gate: the viewer MUST have posted their own moment today
  to see the feed (gate_open == true).
- When gate_open == false, posts is [] and a hint is returned.
- Paginated with limit/offset. has_more == false signals "You're all caught up."
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from verida.api.v1.deps import CurrentUser, get_circle_repo, get_post_repo

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class FeedPostResponse(BaseModel):
    """A single post as shown in the feed."""

    id: str = Field(description="Post UUID.")
    author_id: str = Field(description="Author's user UUID.")
    caption: str = Field(description="Post caption.")
    media_url: str = Field(description="Media URL.")
    media_mime_type: str = Field(description="MIME type of the media.")
    visibility: str = Field(description="Post visibility setting.")
    is_late: bool = Field(description="True if submitted after the 10-minute capture window.")
    published_at: datetime | None = Field(description="Publication timestamp.")
    attestation_status: str | None = Field(
        default=None, description="Attestation status if available."
    )


class FeedResponse(BaseModel):
    """Paginated feed response."""

    posts: list[FeedPostResponse] = Field(description="Posts in this page.")
    has_more: bool = Field(
        description=(
            "True if there are more posts on the next page. "
            "False means 'You're all caught up'."
        )
    )
    gate_open: bool = Field(
        description=(
            "True if the viewer has posted their own moment today and can see the feed. "
            "False means the viewer must post first (reciprocity gate)."
        )
    )
    gate_hint: str | None = Field(
        default=None,
        description=(
            "Human-readable message when gate_open is False, "
            "explaining why the feed is not visible."
        ),
    )
    offset: int = Field(description="Current page offset.")
    limit: int = Field(description="Current page size.")


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=FeedResponse,
    summary="Get the reciprocity-gated daily feed",
    description=(
        "Returns today's posts from users in the viewer's circles. "
        "**Reciprocity gate**: you must post your own daily moment before you can see others'. "
        "Feed is chronological (oldest-first), not engagement-ranked. "
        "`has_more: false` means 'You're all caught up'."
    ),
)
async def get_feed(
    current_user: CurrentUser,
    post_repo: Annotated[Any, Depends(get_post_repo)],
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
    limit: int = Query(default=20, ge=1, le=50, description="Posts per page (max 50)."),
    offset: int = Query(default=0, ge=0, description="Number of posts to skip."),
) -> FeedResponse:
    from verida.application.use_cases.feed import GetFeedUseCase

    use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
    page = await use_case.execute(
        viewer_id=current_user.id,
        today=date.today(),
        limit=limit,
        offset=offset,
    )

    if not page.gate_open:
        return FeedResponse(
            posts=[],
            has_more=False,
            gate_open=False,
            gate_hint=(
                "Post your daily moment first to unlock today's feed. "
                "Tap the camera button to capture your moment."
            ),
            offset=offset,
            limit=limit,
        )

    feed_posts = [
        FeedPostResponse(
            id=str(p.id),
            author_id=str(p.author_id),
            caption=p.caption,
            media_url=p.media_url,
            media_mime_type=p.media_mime_type,
            visibility=p.visibility.value,
            is_late=p.is_late,
            published_at=p.published_at,
            attestation_status=(
                p.attestation.status.value if p.attestation else None
            ),
        )
        for p in page.posts
    ]

    return FeedResponse(
        posts=feed_posts,
        has_more=page.has_more,
        gate_open=True,
        gate_hint=None,
        offset=offset,
        limit=limit,
    )
