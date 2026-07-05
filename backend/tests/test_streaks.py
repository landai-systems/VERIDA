"""Tests for streak tracking — M3.

Tests:
- Streak increment on consecutive days
- Grace day usage (miss 1-2 days, streak preserved)
- Streak reset after grace days exhausted
- Monthly grace day reset
- Idempotent: posting twice in a day doesn't increment streak twice
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Optional

import pytest

from verida.application.use_cases.streaks import (
    GetStreakUseCase,
    UpdateStreakUseCase,
)
from verida.domain.entities import UserStreak


# ── Fake repository ────────────────────────────────────────────────────────────


class FakeStreakRepository:
    def __init__(self) -> None:
        self._streaks: dict[uuid.UUID, UserStreak] = {}

    async def get_for_user(self, user_id: uuid.UUID) -> Optional[UserStreak]:
        return self._streaks.get(user_id)

    async def save(self, streak: UserStreak) -> None:
        self._streaks[streak.user_id] = streak

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        self._streaks.pop(user_id, None)


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_post_starts_streak_at_one() -> None:
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    streak = await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))

    assert streak.current_streak == 1
    assert streak.longest_streak == 1
    assert streak.last_post_date == date(2024, 6, 1)


@pytest.mark.asyncio
async def test_consecutive_days_increment_streak() -> None:
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    for day in range(1, 6):  # 5 consecutive days
        await uc.execute(user_id=user_id, post_date=date(2024, 6, day))

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 5
    assert streak.longest_streak == 5


@pytest.mark.asyncio
async def test_same_day_post_is_idempotent() -> None:
    """Posting twice in the same day should not increment the streak twice."""
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))  # Same day

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 1  # NOT 2


@pytest.mark.asyncio
async def test_one_missed_day_uses_grace_day() -> None:
    """Missing 1 day uses a grace day but preserves the streak."""
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))
    # Skip June 2 (1 missed day)
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 3))

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 2  # Preserved via grace day
    assert streak.grace_days_used_this_month == 1


@pytest.mark.asyncio
async def test_two_missed_days_both_use_grace() -> None:
    """Missing 2 days uses both grace days but streak is preserved."""
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))
    # Skip June 2 and 3 (2 missed days)
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 4))

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 2
    assert streak.grace_days_used_this_month == 2


@pytest.mark.asyncio
async def test_three_missed_days_resets_streak() -> None:
    """Missing 3 days exceeds grace allowance — streak resets to 1."""
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    await uc.execute(user_id=user_id, post_date=date(2024, 6, 1))
    # Skip June 2, 3, 4 (3 missed days — exceeds max 2 grace days)
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 5))

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 1  # Reset


@pytest.mark.asyncio
async def test_grace_days_reset_on_new_month() -> None:
    """Grace day counter resets on the 1st of each month."""
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    # Build up 5-day streak through June
    for day in range(1, 6):
        await uc.execute(user_id=user_id, post_date=date(2024, 6, day))

    # Use 2 grace days in June (skip June 6 and 7, post June 8 — 2 missed days)
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 8))
    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.grace_days_used_this_month == 2

    # Now post on July 1 — grace counter should reset
    # July 1 is more than 2 days after June 8, so streak resets too — that's fine for this test
    await uc.execute(user_id=user_id, post_date=date(2024, 7, 1))
    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.grace_days_used_this_month == 0  # Reset for new month
    assert streak.grace_month == "2024-07"  # Grace tracking moved to July


@pytest.mark.asyncio
async def test_longest_streak_tracks_maximum() -> None:
    repo = FakeStreakRepository()
    uc = UpdateStreakUseCase(repo)
    user_id = uuid.uuid4()

    # Build streak to 5
    for day in range(1, 6):
        await uc.execute(user_id=user_id, post_date=date(2024, 6, day))

    # Break streak
    await uc.execute(user_id=user_id, post_date=date(2024, 6, 10))  # 4-day gap

    streak = await repo.get_for_user(user_id)
    assert streak is not None
    assert streak.current_streak == 1
    assert streak.longest_streak == 5  # Longest preserved


@pytest.mark.asyncio
async def test_get_streak_returns_none_if_never_posted() -> None:
    repo = FakeStreakRepository()
    uc = GetStreakUseCase(repo)

    streak = await uc.execute(uuid.uuid4())
    assert streak is None


@pytest.mark.asyncio
async def test_get_streak_returns_existing() -> None:
    repo = FakeStreakRepository()
    user_id = uuid.uuid4()

    # Set up via update
    update_uc = UpdateStreakUseCase(repo)
    await update_uc.execute(user_id=user_id, post_date=date(2024, 6, 1))

    get_uc = GetStreakUseCase(repo)
    streak = await get_uc.execute(user_id)
    assert streak is not None
    assert streak.current_streak == 1
