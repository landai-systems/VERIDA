"""Circles CRUD + membership endpoints.

GET    /api/v1/circles                     — list circles the authenticated user belongs to
POST   /api/v1/circles                     — create a new circle
GET    /api/v1/circles/{circle_id}         — get circle details + member list
PUT    /api/v1/circles/{circle_id}         — update circle name/description
DELETE /api/v1/circles/{circle_id}         — delete a circle (owner only)
POST   /api/v1/circles/{circle_id}/invite  — invite a user (owner/moderator only)
POST   /api/v1/circles/{circle_id}/accept  — accept an invitation
DELETE /api/v1/circles/{circle_id}/members/{user_id}  — remove a member / leave
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from verida.api.v1.deps import (
    CurrentUser,
    get_circle_repo,
    get_user_repo,
)
from verida.domain.entities import CircleRole

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class CreateCircleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="Circle name.")
    description: str = Field(default="", max_length=500, description="Optional description.")
    is_private: bool = Field(default=True, description="If True, join requires an invitation.")


class UpdateCircleRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class InviteMemberRequest(BaseModel):
    user_id: str = Field(..., description="UUID of the user to invite.")


class CircleResponse(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    is_private: bool
    member_count: int
    created_at: datetime
    updated_at: datetime


class MemberResponse(BaseModel):
    user_id: str
    role: str
    invite_status: str
    joined_at: datetime


class CircleDetailResponse(BaseModel):
    circle: CircleResponse
    members: list[MemberResponse]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[CircleResponse],
    summary="List circles the authenticated user belongs to",
)
async def list_circles(
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> list[CircleResponse]:
    from verida.application.use_cases.circles import ListCirclesUseCase

    circles = await ListCirclesUseCase(circle_repo).execute(current_user.id)
    result = []
    for c in circles:
        count = await circle_repo.count_members(c.id)
        result.append(
            CircleResponse(
                id=str(c.id),
                name=c.name,
                description=c.description,
                owner_id=str(c.owner_id),
                is_private=c.is_private,
                member_count=count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return result


@router.post(
    "",
    response_model=CircleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new circle",
)
async def create_circle(
    body: CreateCircleRequest,
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> CircleResponse:
    from verida.application.use_cases.circles import CreateCircleUseCase

    circle = await CreateCircleUseCase(circle_repo).execute(
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
        is_private=body.is_private,
    )
    return CircleResponse(
        id=str(circle.id),
        name=circle.name,
        description=circle.description,
        owner_id=str(circle.owner_id),
        is_private=circle.is_private,
        member_count=1,  # just the owner
        created_at=circle.created_at,
        updated_at=circle.updated_at,
    )


@router.get(
    "/{circle_id}",
    response_model=CircleDetailResponse,
    summary="Get circle details and member list",
)
async def get_circle(
    circle_id: Annotated[str, Path(description="Circle UUID")],
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> CircleDetailResponse:
    cid = uuid.UUID(circle_id)
    circle = await circle_repo.get_by_id(cid)
    if circle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

    # Must be a member to view details
    membership = await circle_repo.get_membership(cid, current_user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    members = await circle_repo.list_members(cid)
    accepted = [m for m in members if m.invite_status.value == "accepted"]

    return CircleDetailResponse(
        circle=CircleResponse(
            id=str(circle.id),
            name=circle.name,
            description=circle.description,
            owner_id=str(circle.owner_id),
            is_private=circle.is_private,
            member_count=len(accepted),
            created_at=circle.created_at,
            updated_at=circle.updated_at,
        ),
        members=[
            MemberResponse(
                user_id=str(m.user_id),
                role=m.role.value,
                invite_status=m.invite_status.value,
                joined_at=m.joined_at,
            )
            for m in members
        ],
    )


@router.put(
    "/{circle_id}",
    response_model=CircleResponse,
    summary="Update circle name or description (owner only)",
)
async def update_circle(
    circle_id: Annotated[str, Path()],
    body: UpdateCircleRequest,
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> CircleResponse:
    from datetime import UTC

    cid = uuid.UUID(circle_id)
    circle = await circle_repo.get_by_id(cid)
    if circle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

    if circle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the circle owner can update it.",
        )

    if body.name is not None:
        circle.name = body.name
    if body.description is not None:
        circle.description = body.description
    from datetime import UTC, datetime
    circle.updated_at = datetime.now(UTC)

    await circle_repo.save(circle)
    count = await circle_repo.count_members(cid)

    return CircleResponse(
        id=str(circle.id),
        name=circle.name,
        description=circle.description,
        owner_id=str(circle.owner_id),
        is_private=circle.is_private,
        member_count=count,
        created_at=circle.created_at,
        updated_at=circle.updated_at,
    )


@router.delete(
    "/{circle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a circle (owner only)",
)
async def delete_circle(
    circle_id: Annotated[str, Path()],
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> None:
    cid = uuid.UUID(circle_id)
    circle = await circle_repo.get_by_id(cid)
    if circle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

    if circle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the circle owner can delete it.",
        )

    await circle_repo.delete(cid)


@router.post(
    "/{circle_id}/invite",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to this circle",
)
async def invite_member(
    circle_id: Annotated[str, Path()],
    body: InviteMemberRequest,
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
    user_repo: Annotated[Any, Depends(get_user_repo)],
) -> MemberResponse:
    from verida.application.use_cases.circles import InviteMemberUseCase

    try:
        membership = await InviteMemberUseCase(circle_repo, user_repo).execute(
            circle_id=uuid.UUID(circle_id),
            inviter_id=current_user.id,
            invitee_id=uuid.UUID(body.user_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return MemberResponse(
        user_id=str(membership.user_id),
        role=membership.role.value,
        invite_status=membership.invite_status.value,
        joined_at=membership.joined_at,
    )


@router.post(
    "/{circle_id}/accept",
    response_model=MemberResponse,
    summary="Accept a pending circle invitation",
)
async def accept_invite(
    circle_id: Annotated[str, Path()],
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> MemberResponse:
    from verida.application.use_cases.circles import AcceptInviteUseCase

    try:
        membership = await AcceptInviteUseCase(circle_repo).execute(
            circle_id=uuid.UUID(circle_id),
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return MemberResponse(
        user_id=str(membership.user_id),
        role=membership.role.value,
        invite_status=membership.invite_status.value,
        joined_at=membership.joined_at,
    )


@router.delete(
    "/{circle_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a circle or leave (self-removal)",
)
async def remove_member(
    circle_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    current_user: CurrentUser,
    circle_repo: Annotated[Any, Depends(get_circle_repo)],
) -> None:
    from verida.application.use_cases.circles import RemoveMemberUseCase

    try:
        await RemoveMemberUseCase(circle_repo).execute(
            circle_id=uuid.UUID(circle_id),
            requester_id=current_user.id,
            target_user_id=uuid.UUID(user_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
