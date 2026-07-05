"""Tests for reactions — M3.

Tests:
- Add a reaction
- Remove a reaction
- Idempotent add (same emoji twice)
- No public counters (GetReactionsUseCase returns only current user's reactions)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

import pytest

from verida.application.use_cases.reactions import (
    AddReactionUseCase,
    GetReactionsUseCase,
    RemoveReactionUseCase,
)
from verida.domain.entities import Reaction, ReactionEmoji


# ── Fake repository ────────────────────────────────────────────────────────────


class FakeReactionRepository:
    def __init__(self) -> None:
        self._reactions: dict[uuid.UUID, Reaction] = {}

    async def get(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: ReactionEmoji,
    ) -> Optional[Reaction]:
        for r in self._reactions.values():
            if r.post_id == post_id and r.user_id == user_id and r.emoji == emoji:
                return r
        return None

    async def save(self, reaction: Reaction) -> None:
        self._reactions[reaction.id] = reaction

    async def delete(self, reaction_id: uuid.UUID) -> None:
        self._reactions.pop(reaction_id, None)

    async def list_by_user_on_post(
        self, post_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Reaction]:
        return [
            r for r in self._reactions.values()
            if r.post_id == post_id and r.user_id == user_id
        ]

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 1000) -> list[Reaction]:
        return [r for r in self._reactions.values() if r.user_id == user_id]

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        to_del = [rid for rid, r in self._reactions.items() if r.user_id == user_id]
        for rid in to_del:
            del self._reactions[rid]


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_reaction_creates_reaction() -> None:
    repo = FakeReactionRepository()
    uc = AddReactionUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    reaction = await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.HEART)

    assert reaction.post_id == post_id
    assert reaction.user_id == user_id
    assert reaction.emoji == ReactionEmoji.HEART


@pytest.mark.asyncio
async def test_add_reaction_idempotent() -> None:
    """Adding the same emoji twice returns the existing reaction, not a duplicate."""
    repo = FakeReactionRepository()
    uc = AddReactionUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    r1 = await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.FIRE)
    r2 = await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.FIRE)

    assert r1.id == r2.id
    # Only one reaction in the repo
    all_reactions = await repo.list_by_user(user_id)
    assert len(all_reactions) == 1


@pytest.mark.asyncio
async def test_add_different_emojis_allowed() -> None:
    """User can react with multiple different emojis on the same post."""
    repo = FakeReactionRepository()
    uc = AddReactionUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.HEART)
    await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.SMILE)

    all_reactions = await repo.list_by_user(user_id)
    assert len(all_reactions) == 2


@pytest.mark.asyncio
async def test_remove_reaction_returns_true() -> None:
    repo = FakeReactionRepository()
    add_uc = AddReactionUseCase(repo)
    remove_uc = RemoveReactionUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await add_uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.STAR)
    removed = await remove_uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.STAR)

    assert removed is True
    all_reactions = await repo.list_by_user(user_id)
    assert len(all_reactions) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_reaction_returns_false() -> None:
    repo = FakeReactionRepository()
    uc = RemoveReactionUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    removed = await uc.execute(post_id=post_id, user_id=user_id, emoji=ReactionEmoji.HUG)
    assert removed is False


@pytest.mark.asyncio
async def test_get_reactions_returns_only_current_user() -> None:
    """NO PUBLIC COUNTERS: GetReactionsUseCase must only return the current user's reactions."""
    repo = FakeReactionRepository()
    add_uc = AddReactionUseCase(repo)
    get_uc = GetReactionsUseCase(repo)

    post_id = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()  # different user

    # Both users react to the same post
    await add_uc.execute(post_id=post_id, user_id=user_a, emoji=ReactionEmoji.HEART)
    await add_uc.execute(post_id=post_id, user_id=user_b, emoji=ReactionEmoji.FIRE)

    # user_a's view — should ONLY see their own reaction
    reactions_for_a = await get_uc.execute(post_id=post_id, current_user_id=user_a)
    assert len(reactions_for_a) == 1
    assert reactions_for_a[0].emoji == ReactionEmoji.HEART
    assert reactions_for_a[0].user_id == user_a
    # Critically: user_b's reaction is NOT included
    for r in reactions_for_a:
        assert r.user_id == user_a


@pytest.mark.asyncio
async def test_get_reactions_empty_when_no_reactions() -> None:
    repo = FakeReactionRepository()
    uc = GetReactionsUseCase(repo)
    post_id = uuid.uuid4()
    user_id = uuid.uuid4()

    reactions = await uc.execute(post_id=post_id, current_user_id=user_id)
    assert reactions == []


@pytest.mark.asyncio
async def test_only_warm_emojis_allowed() -> None:
    """Verify the allowed emoji set matches spec (warm, positive only)."""
    allowed = {e.value for e in ReactionEmoji}
    # Required emoji
    assert "\u2764\ufe0f" in allowed   # ❤️
    assert "\U0001f60a" in allowed     # 😊
    assert "\U0001f525" in allowed     # 🔥
    assert "\U0001f31f" in allowed     # 🌟
    assert "\U0001f917" in allowed     # 🤗
    # No negative emoji
    assert "\U0001f44e" not in allowed  # 👎
    assert "\U0001f620" not in allowed  # 😠
