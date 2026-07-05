"""Tests for GDPR export and erasure — M3.

Tests:
- Export completeness (all entity types included)
- Delete cascade (all user data removed)
- Purge job is scheduled
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, date
from typing import Any, Optional

import pytest

from verida.application.use_cases.gdpr import DeleteUserDataUseCase, ExportUserDataUseCase
from verida.domain.entities import (
    Circle,
    Comment,
    ConsentRecord,
    ConsentType,
    Post,
    PostVisibility,
    Reaction,
    ReactionEmoji,
    User,
    UserStreak,
)


# ── Fake repositories ─────────────────────────────────────────────────────────


class FakeUserRepo:
    def __init__(self, user: User) -> None:
        self._user = user
        self.deleted: list[uuid.UUID] = []
        self.saved: list[User] = []

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        if self._user.id == user_id:
            return self._user
        return None

    async def save(self, user: User) -> None:
        self._user = user
        self.saved.append(user)

    async def delete(self, user_id: uuid.UUID) -> None:
        self.deleted.append(user_id)


class FakePostRepo:
    def __init__(self, posts: list[Post]) -> None:
        self._posts = posts

    async def list_by_author(self, author_id: uuid.UUID, limit: int = 1000) -> list[Post]:
        return [p for p in self._posts if p.author_id == author_id]


class FakeCircleRepo:
    def __init__(self, circles: list[Circle]) -> None:
        self._circles = circles

    async def list_for_member(self, user_id: uuid.UUID) -> list[Circle]:
        return self._circles


class FakeConsentRepo:
    def __init__(self, records: list[ConsentRecord]) -> None:
        self._records = records

    async def list_for_user(
        self, user_id: uuid.UUID, consent_type: Any = None
    ) -> list[ConsentRecord]:
        return [r for r in self._records if r.user_id == user_id]

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        self._records = [r for r in self._records if r.user_id != user_id]


class FakeCommentRepo:
    def __init__(self, comments: list[Comment]) -> None:
        self._comments = comments
        self.deleted_by_author: list[uuid.UUID] = []

    async def list_by_author(self, author_id: uuid.UUID, limit: int = 1000) -> list[Comment]:
        return [c for c in self._comments if c.author_id == author_id]

    async def delete_all_by_author(self, author_id: uuid.UUID) -> None:
        self.deleted_by_author.append(author_id)
        self._comments = [c for c in self._comments if c.author_id != author_id]


class FakeReactionRepo:
    def __init__(self, reactions: list[Reaction]) -> None:
        self._reactions = reactions
        self.deleted_by_user: list[uuid.UUID] = []

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 1000) -> list[Reaction]:
        return [r for r in self._reactions if r.user_id == user_id]

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        self.deleted_by_user.append(user_id)
        self._reactions = [r for r in self._reactions if r.user_id != user_id]


class FakeStreakRepo:
    def __init__(self, streak: Optional[UserStreak]) -> None:
        self._streak = streak
        self.deleted: list[uuid.UUID] = []

    async def get_for_user(self, user_id: uuid.UUID) -> Optional[UserStreak]:
        if self._streak and self._streak.user_id == user_id:
            return self._streak
        return None

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        self.deleted.append(user_id)
        self._streak = None


class FakeArqPool:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, ...]] = []

    async def enqueue_job(self, task_name: str, *args: Any) -> None:
        self.enqueued.append((task_name, *args))


# ── Test data factories ────────────────────────────────────────────────────────


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        handle="testuser",
        email="test@example.com",
        display_name="Test User",
        argon2_hash="$argon2id$v=19$hashed",
    )


def _make_post(author_id: uuid.UUID) -> Post:
    return Post(
        author_id=author_id,
        daily_moment_id=uuid.uuid4(),
        caption="Hello world",
        media_url="https://cdn.example.com/photo.jpg",
        media_hash="a" * 64,
        media_mime_type="image/jpeg",
    )


# ── Export tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_includes_all_entity_types() -> None:
    user = _make_user()
    post = _make_post(user.id)
    circle = Circle(id=uuid.uuid4(), name="Friends", owner_id=user.id)
    consent = ConsentRecord(
        user_id=user.id,
        consent_type=ConsentType.TERMS_OF_SERVICE,
        version="1.0",
        text_version="hash",
        ip_hash="h",
    )
    comment = Comment(post_id=post.id, author_id=user.id, body="Nice post!")
    reaction = Reaction(post_id=post.id, user_id=user.id, emoji=ReactionEmoji.HEART)
    streak = UserStreak(user_id=user.id, current_streak=5, longest_streak=10)

    uc = ExportUserDataUseCase(
        user_repo=FakeUserRepo(user),
        post_repo=FakePostRepo([post]),
        circle_repo=FakeCircleRepo([circle]),
        consent_repo=FakeConsentRepo([consent]),
        comment_repo=FakeCommentRepo([comment]),
        reaction_repo=FakeReactionRepo([reaction]),
        streak_repo=FakeStreakRepo(streak),
    )

    export = await uc.execute(user.id)

    # Top-level structure
    assert "user" in export
    assert "posts" in export
    assert "circles" in export
    assert "consent_records" in export
    assert "comments" in export
    assert "reactions" in export
    assert "streak" in export
    assert "exported_at" in export
    assert "gdpr_article" in export

    # Sensitive field excluded
    assert "argon2_hash" not in export["user"]

    # Content correct
    assert export["user"]["email"] == user.email
    assert len(export["posts"]) == 1
    assert len(export["circles"]) == 1
    assert len(export["consent_records"]) == 1
    assert len(export["comments"]) == 1
    assert len(export["reactions"]) == 1
    assert export["streak"]["current_streak"] == 5


@pytest.mark.asyncio
async def test_export_raises_if_user_not_found() -> None:
    user = _make_user()
    wrong_id = uuid.uuid4()

    uc = ExportUserDataUseCase(
        user_repo=FakeUserRepo(user),
        post_repo=FakePostRepo([]),
        circle_repo=FakeCircleRepo([]),
        consent_repo=FakeConsentRepo([]),
        comment_repo=FakeCommentRepo([]),
        reaction_repo=FakeReactionRepo([]),
        streak_repo=FakeStreakRepo(None),
    )

    with pytest.raises(ValueError, match="User not found"):
        await uc.execute(wrong_id)


# ── Delete tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_cascade_removes_all_personal_data() -> None:
    user = _make_user()
    comment_repo = FakeCommentRepo([Comment(post_id=uuid.uuid4(), author_id=user.id, body="hi")])
    reaction_repo = FakeReactionRepo(
        [Reaction(post_id=uuid.uuid4(), user_id=user.id, emoji=ReactionEmoji.STAR)]
    )
    streak_repo = FakeStreakRepo(UserStreak(user_id=user.id, current_streak=3))
    user_repo = FakeUserRepo(user)
    arq_pool = FakeArqPool()

    uc = DeleteUserDataUseCase(
        user_repo=user_repo,
        post_repo=FakePostRepo([]),
        consent_repo=FakeConsentRepo([]),
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        streak_repo=streak_repo,
        arq_pool=arq_pool,
    )

    summary = await uc.execute(user.id)

    # User hard-deleted
    assert user.id in user_repo.deleted

    # Comments deleted
    assert user.id in comment_repo.deleted_by_author

    # Reactions deleted
    assert user.id in reaction_repo.deleted_by_user

    # Streak deleted
    assert user.id in streak_repo.deleted

    # Purge job scheduled
    assert ("purge_deleted_user_data", str(user.id)) in arq_pool.enqueued

    assert "user_row_deleted" in summary["steps"]


@pytest.mark.asyncio
async def test_delete_schedules_purge_job() -> None:
    user = _make_user()
    arq_pool = FakeArqPool()

    uc = DeleteUserDataUseCase(
        user_repo=FakeUserRepo(user),
        post_repo=FakePostRepo([]),
        consent_repo=FakeConsentRepo([]),
        comment_repo=FakeCommentRepo([]),
        reaction_repo=FakeReactionRepo([]),
        streak_repo=FakeStreakRepo(None),
        arq_pool=arq_pool,
    )

    await uc.execute(user.id)

    assert len(arq_pool.enqueued) == 1
    assert arq_pool.enqueued[0][0] == "purge_deleted_user_data"


@pytest.mark.asyncio
async def test_delete_without_arq_pool_still_completes() -> None:
    """Deletion should succeed even without arq pool (dev/test environment)."""
    user = _make_user()

    uc = DeleteUserDataUseCase(
        user_repo=FakeUserRepo(user),
        post_repo=FakePostRepo([]),
        consent_repo=FakeConsentRepo([]),
        comment_repo=FakeCommentRepo([]),
        reaction_repo=FakeReactionRepo([]),
        streak_repo=FakeStreakRepo(None),
        arq_pool=None,
    )

    summary = await uc.execute(user.id)
    assert "user_row_deleted" in summary["steps"]
    assert "purge_job_not_scheduled_no_pool" in summary["steps"]
