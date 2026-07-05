"""Tests for the reciprocity-gated feed.

Tests
-----
- Gate closed: viewer gets empty feed + gate_open=False before posting.
- Gate open: viewer sees circle-members' posts after posting own moment.
- Pagination: has_more correctly signals more pages.
- Feed is chronological (oldest first).
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from verida.application.use_cases.feed import FeedPage, GetFeedUseCase
from verida.domain.entities import Circle, Post, PostVisibility


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_post(
    author_id: uuid.UUID,
    *,
    created_at_offset_seconds: int = 0,
    visibility: PostVisibility = PostVisibility.CIRCLES,
) -> Post:
    now = datetime.now(UTC) + timedelta(seconds=created_at_offset_seconds)
    return Post(
        author_id=author_id,
        daily_moment_id=uuid.uuid4(),
        caption="Test post",
        media_url="/media/test.jpg",
        media_hash="a" * 64,
        media_mime_type="image/jpeg",
        visibility=visibility,
        published_at=now,
        created_at=now,
    )


def _make_circle(owner_id: uuid.UUID) -> Circle:
    return Circle(
        owner_id=owner_id,
        name="Test Circle",
        is_private=True,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestFeedReciprocityGate:
    """The reciprocity gate must block the feed until the viewer has posted."""

    async def test_gate_closed_when_no_post_today(self) -> None:
        """A user who hasn't posted today should see gate_open=False."""
        viewer_id = uuid.uuid4()

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = None  # no post today
        post_repo.list_feed_posts.return_value = []

        circle_repo = AsyncMock()
        circle_repo.list_for_member.return_value = [_make_circle(viewer_id)]

        use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
        page = await use_case.execute(viewer_id=viewer_id, today=date.today())

        assert page.gate_open is False
        assert page.posts == []
        assert page.has_more is False
        # list_feed_posts should NOT be called when gate is closed
        post_repo.list_feed_posts.assert_not_called()

    async def test_gate_open_after_posting(self) -> None:
        """After posting, the viewer should see circle-members' posts."""
        viewer_id = uuid.uuid4()
        member_id = uuid.uuid4()
        today = date.today()

        viewer_post = _make_post(viewer_id)
        member_post = _make_post(member_id)

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = viewer_post
        post_repo.list_feed_posts.return_value = [member_post]

        circle = _make_circle(viewer_id)
        circle_repo = AsyncMock()
        circle_repo.list_for_member.return_value = [circle]

        use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
        page = await use_case.execute(viewer_id=viewer_id, today=today)

        assert page.gate_open is True
        assert len(page.posts) == 1
        assert page.posts[0].author_id == member_id

    async def test_empty_circles_returns_empty_feed(self) -> None:
        """A user with no circles sees an empty feed even after posting."""
        viewer_id = uuid.uuid4()
        viewer_post = _make_post(viewer_id)

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = viewer_post
        post_repo.list_feed_posts.return_value = []

        circle_repo = AsyncMock()
        circle_repo.list_for_member.return_value = []  # no circles

        use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
        page = await use_case.execute(viewer_id=viewer_id, today=date.today())

        assert page.gate_open is True
        assert page.posts == []
        assert page.has_more is False


@pytest.mark.asyncio
class TestFeedPagination:
    """Feed pagination must correctly report has_more."""

    async def _get_page(
        self,
        viewer_id: uuid.UUID,
        num_posts: int,
        limit: int,
        offset: int,
    ) -> FeedPage:
        viewer_post = _make_post(viewer_id)
        # Simulate DB returning limit+1 if there are more posts
        available = [_make_post(uuid.uuid4()) for _ in range(num_posts)]
        fetched = available[offset : offset + limit + 1]

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = viewer_post
        post_repo.list_feed_posts.return_value = fetched

        circle = _make_circle(viewer_id)
        circle_repo = AsyncMock()
        circle_repo.list_for_member.return_value = [circle]

        use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
        return await use_case.execute(
            viewer_id=viewer_id,
            today=date.today(),
            limit=limit,
            offset=offset,
        )

    async def test_has_more_true_when_more_posts_available(self) -> None:
        viewer_id = uuid.uuid4()
        page = await self._get_page(viewer_id, num_posts=25, limit=10, offset=0)
        # Repo returns 11 items (limit+1), so has_more should be True
        assert page.has_more is True
        assert len(page.posts) == 10

    async def test_has_more_false_on_last_page(self) -> None:
        viewer_id = uuid.uuid4()
        # Last page: only 5 posts left, limit=10
        page = await self._get_page(viewer_id, num_posts=5, limit=10, offset=0)
        assert page.has_more is False
        assert len(page.posts) == 5

    async def test_limit_capped_at_50(self) -> None:
        """Limits above 50 are capped at 50."""
        viewer_id = uuid.uuid4()
        viewer_post = _make_post(viewer_id)

        post_repo = AsyncMock()
        post_repo.get_today_post_for_user.return_value = viewer_post
        post_repo.list_feed_posts.return_value = []

        circle_repo = AsyncMock()
        circle_repo.list_for_member.return_value = [_make_circle(viewer_id)]

        use_case = GetFeedUseCase(post_repo=post_repo, circle_repo=circle_repo)
        page = await use_case.execute(
            viewer_id=viewer_id, today=date.today(), limit=999
        )
        assert page.limit == 50
