"""Use case: Get the chronological, reciprocity-gated feed.

Reciprocity rule:
    A user can only see today's feed AFTER they have submitted their own
    daily moment post for today.  If they have not posted, the feed returns
    an empty list with a ``gate_open: false`` flag.

Feed characteristics:
    - Chronological (oldest-first within today's posts)
    - Circle-filtered: only posts from people in the viewer's circles
    - Paginated: ``limit`` + ``offset`` (default 20 per page)
    - ``has_more`` indicates whether another page exists
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import structlog

from verida.application.ports import CircleRepository, PostRepository
from verida.domain.entities import Post

logger = structlog.get_logger(__name__)


@dataclass
class FeedPage:
    """The result of a paginated feed query."""

    posts: list[Post]
    has_more: bool
    gate_open: bool  # False if user hasn't posted their own moment today
    offset: int
    limit: int


class GetFeedUseCase:
    """Return the reciprocity-gated, chronological feed for a user."""

    def __init__(
        self,
        post_repo: PostRepository,
        circle_repo: CircleRepository,
    ) -> None:
        self._post_repo = post_repo
        self._circle_repo = circle_repo

    async def execute(
        self,
        viewer_id: uuid.UUID,
        today: date | None = None,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> FeedPage:
        """Fetch the feed page.

        Parameters
        ----------
        viewer_id:
            The authenticated user viewing the feed.
        today:
            The date to fetch feed for (defaults to today's UTC date).
        limit:
            Page size (max 50).
        offset:
            Number of posts to skip.
        """
        if today is None:
            from datetime import UTC
            today = date.today()

        limit = min(limit, 50)

        # Reciprocity gate: check if viewer has posted today
        viewer_post = await self._post_repo.get_today_post_for_user(viewer_id, today)
        if viewer_post is None:
            logger.info(
                "feed_gate_closed",
                viewer_id=str(viewer_id),
                date=str(today),
            )
            return FeedPage(
                posts=[],
                has_more=False,
                gate_open=False,
                offset=offset,
                limit=limit,
            )

        # Get circles the viewer belongs to
        circles = await self._circle_repo.list_for_member(viewer_id)
        circle_ids = [c.id for c in circles]

        if not circle_ids:
            return FeedPage(
                posts=[],
                has_more=False,
                gate_open=True,
                offset=offset,
                limit=limit,
            )

        # Fetch limit+1 to determine has_more
        posts = await self._post_repo.list_feed_posts(
            viewer_id=viewer_id,
            circle_ids=circle_ids,
            today=today,
            limit=limit + 1,
            offset=offset,
        )

        has_more = len(posts) > limit
        if has_more:
            posts = posts[:limit]

        logger.info(
            "feed_fetched",
            viewer_id=str(viewer_id),
            count=len(posts),
            has_more=has_more,
        )

        return FeedPage(
            posts=posts,
            has_more=has_more,
            gate_open=True,
            offset=offset,
            limit=limit,
        )
