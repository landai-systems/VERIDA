"""Streak tracking use cases — M3.

Streak mechanics (see docs/ENGAGEMENT.md for full rationale):
- A streak increments when the user posts on consecutive days
- Grace days: up to 2 missed days per calendar month without resetting the streak
- Grace day counter resets on the 1st of each calendar month
- Streaks are POSITIVE-ONLY: no red-dot badges, no guilt-trip copy, no deadlines shown
- The API returns the streak number but NOT "you'll lose it tomorrow" messaging

Design:
- UpdateStreakUseCase is called after a post is successfully submitted
- GetStreakUseCase returns current streak info without update
- Grace-day tracking uses a YYYY-MM string to detect month rollover
"""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Optional

import structlog

from verida.domain.entities import UserStreak

logger = structlog.get_logger(__name__)

MAX_GRACE_DAYS_PER_MONTH = 2


def _days_between(a: date, b: date) -> int:
    """Return absolute number of days between two dates."""
    return abs((b - a).days)


def _month_key(d: date) -> str:
    """Return 'YYYY-MM' key for the given date."""
    return d.strftime("%Y-%m")


class UpdateStreakUseCase:
    """Update a user's streak after a post is submitted.

    Called by the post submission flow immediately after a post is saved.
    """

    def __init__(self, streak_repo: object) -> None:
        self._repo = streak_repo

    async def execute(self, user_id: uuid.UUID, post_date: Optional[date] = None) -> UserStreak:
        """Update the streak for a user after they post.

        Parameters
        ----------
        user_id:
            The posting user.
        post_date:
            The calendar date of the post (UTC). Defaults to today.

        Returns
        -------
        UserStreak:
            The updated streak record.
        """
        today = post_date or datetime.now(UTC).date()
        current_month = _month_key(today)

        streak = await self._repo.get_for_user(user_id)
        if streak is None:
            # First ever post — create new streak
            streak = UserStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                grace_days_used_this_month=0,
                last_post_date=today,
                grace_month=current_month,
            )
        else:
            last = streak.last_post_date

            # Detect grace month rollover — reset counter on new month
            if streak.grace_month != current_month:
                streak.grace_days_used_this_month = 0
                streak.grace_month = current_month

            if last is None:
                # No previous post — start fresh
                streak.current_streak = 1
            elif last == today:
                # Already posted today — idempotent, no change to streak count
                pass
            elif _days_between(last, today) == 1:
                # Posted yesterday — increment streak
                streak.current_streak += 1
            else:
                # Missed one or more days
                missed_days = _days_between(last, today) - 1
                grace_remaining = MAX_GRACE_DAYS_PER_MONTH - streak.grace_days_used_this_month

                if missed_days <= grace_remaining:
                    # Within grace days — extend streak, use grace days
                    streak.grace_days_used_this_month += missed_days
                    streak.current_streak += 1
                else:
                    # Grace exhausted — reset streak (no guilt copy)
                    streak.current_streak = 1
                    # Don't reset grace_days_used — already used this month

            streak.last_post_date = today
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
            streak.updated_at = datetime.now(UTC)

        # Update longest
        streak.longest_streak = max(streak.longest_streak, streak.current_streak)

        await self._repo.save(streak)

        logger.info(
            "streak_updated",
            user_id=str(user_id),
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            grace_days_used=streak.grace_days_used_this_month,
        )

        return streak


class GetStreakUseCase:
    """Get a user's current streak information."""

    def __init__(self, streak_repo: object) -> None:
        self._repo = streak_repo

    async def execute(self, user_id: uuid.UUID) -> Optional[UserStreak]:
        """Get streak data for a user.

        Returns None if the user has never posted.
        """
        return await self._repo.get_for_user(user_id)
