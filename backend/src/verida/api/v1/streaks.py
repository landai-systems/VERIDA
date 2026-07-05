"""Streaks API — M3.

Endpoints:
    GET /api/v1/me/streak — get current user's streak

Design (see docs/ENGAGEMENT.md):
- NO countdown / "you'll lose it in X days" messaging
- NO red-dot badges or guilt-trip copy
- Streaks are purely informational and positive
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter

from verida.api.v1.deps import AsyncSessionDep, CurrentUser

router = APIRouter()


from pydantic import BaseModel


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_post_date: Optional[date]
    # NOTE: We intentionally do NOT include grace_days_remaining or
    # "you'll lose your streak" messages — that creates anxiety and guilt.
    # Streaks are shown as positive achievement only.


@router.get(
    "",
    response_model=StreakResponse,
    summary="Get my current streak",
)
async def get_streak(
    current_user: CurrentUser,
    session: AsyncSessionDep,
) -> StreakResponse:
    """Return the current user's streak information.

    Returns zero-value streak if user has never posted.
    Intentionally omits countdown/deadline information.
    """
    from verida.infrastructure.db.repositories import SqlStreakRepository
    from verida.application.use_cases.streaks import GetStreakUseCase

    repo = SqlStreakRepository(session)
    use_case = GetStreakUseCase(repo)
    streak = await use_case.execute(current_user.id)

    if streak is None:
        return StreakResponse(
            current_streak=0,
            longest_streak=0,
            last_post_date=None,
        )

    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_post_date=streak.last_post_date,
    )
