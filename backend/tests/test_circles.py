"""Tests for Circle management use cases.

Tests
-----
- Create circle: creator auto-added as OWNER.
- Invite: only owner/moderator can invite; max 30 members enforced.
- Accept invite: transitions PENDING → ACCEPTED.
- Remove member: owner can remove, moderator cannot remove owner.
- List circles: returns circles the user belongs to.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from verida.application.use_cases.circles import (
    AcceptInviteUseCase,
    CreateCircleUseCase,
    InviteMemberUseCase,
    ListCirclesUseCase,
    RemoveMemberUseCase,
)
from verida.domain.entities import (
    Circle,
    CircleMembership,
    CircleRole,
    InviteStatus,
    User,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(handle: str = "alice") -> User:
    return User(handle=handle, email=f"{handle}@example.com", display_name=handle)


def _make_circle(owner_id: uuid.UUID) -> Circle:
    return Circle(owner_id=owner_id, name="My Circle")


def _make_membership(
    circle_id: uuid.UUID,
    user_id: uuid.UUID,
    role: CircleRole = CircleRole.MEMBER,
    invite_status: InviteStatus = InviteStatus.ACCEPTED,
) -> CircleMembership:
    return CircleMembership(
        circle_id=circle_id,
        user_id=user_id,
        role=role,
        invite_status=invite_status,
    )


# ── Create Circle ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateCircle:
    async def test_creates_circle_and_owner_membership(self) -> None:
        owner = _make_user("alice")
        circle_repo = AsyncMock()
        circle_repo.save.return_value = None
        circle_repo.save_membership.return_value = None

        use_case = CreateCircleUseCase(circle_repo)
        circle = await use_case.execute(
            owner_id=owner.id,
            name="Close Friends",
            description="My inner circle",
        )

        assert circle.owner_id == owner.id
        assert circle.name == "Close Friends"
        assert circle_repo.save.called
        assert circle_repo.save_membership.called

        # Verify the membership saved is OWNER role
        saved_membership: CircleMembership = circle_repo.save_membership.call_args[0][0]
        assert saved_membership.user_id == owner.id
        assert saved_membership.role == CircleRole.OWNER
        assert saved_membership.invite_status == InviteStatus.ACCEPTED


# ── Invite Member ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestInviteMember:
    async def test_owner_can_invite(self) -> None:
        owner = _make_user("alice")
        invitee = _make_user("bob")
        circle = _make_circle(owner.id)

        owner_membership = _make_membership(circle.id, owner.id, role=CircleRole.OWNER)

        circle_repo = AsyncMock()
        circle_repo.get_by_id.return_value = circle
        circle_repo.get_membership.side_effect = lambda cid, uid: (
            owner_membership if uid == owner.id else None
        )
        circle_repo.count_members.return_value = 1
        circle_repo.save_membership.return_value = None

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = invitee

        use_case = InviteMemberUseCase(circle_repo, user_repo)
        membership = await use_case.execute(
            circle_id=circle.id,
            inviter_id=owner.id,
            invitee_id=invitee.id,
        )

        assert membership.user_id == invitee.id
        assert membership.invite_status == InviteStatus.PENDING
        assert membership.invited_by == owner.id

    async def test_regular_member_cannot_invite(self) -> None:
        member = _make_user("carol")
        invitee = _make_user("dave")
        owner = _make_user("alice")
        circle = _make_circle(owner.id)

        member_membership = _make_membership(circle.id, member.id, role=CircleRole.MEMBER)

        circle_repo = AsyncMock()
        circle_repo.get_by_id.return_value = circle
        circle_repo.get_membership.return_value = member_membership

        user_repo = AsyncMock()

        use_case = InviteMemberUseCase(circle_repo, user_repo)

        with pytest.raises(PermissionError):
            await use_case.execute(
                circle_id=circle.id,
                inviter_id=member.id,
                invitee_id=invitee.id,
            )

    async def test_max_30_members_enforced(self) -> None:
        owner = _make_user("alice")
        invitee = _make_user("extra")
        circle = _make_circle(owner.id)
        owner_membership = _make_membership(circle.id, owner.id, role=CircleRole.OWNER)

        circle_repo = AsyncMock()
        circle_repo.get_by_id.return_value = circle
        circle_repo.get_membership.side_effect = lambda cid, uid: (
            owner_membership if uid == owner.id else None
        )
        circle_repo.count_members.return_value = 30  # already at max

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = invitee

        use_case = InviteMemberUseCase(circle_repo, user_repo)

        with pytest.raises(ValueError, match="maximum of 30 members"):
            await use_case.execute(
                circle_id=circle.id,
                inviter_id=owner.id,
                invitee_id=invitee.id,
            )

    async def test_cannot_invite_existing_member(self) -> None:
        owner = _make_user("alice")
        invitee = _make_user("bob")
        circle = _make_circle(owner.id)
        owner_membership = _make_membership(circle.id, owner.id, role=CircleRole.OWNER)
        existing_membership = _make_membership(circle.id, invitee.id)

        circle_repo = AsyncMock()
        circle_repo.get_by_id.return_value = circle
        circle_repo.get_membership.side_effect = lambda cid, uid: (
            owner_membership if uid == owner.id else existing_membership
        )
        circle_repo.count_members.return_value = 2

        user_repo = AsyncMock()

        use_case = InviteMemberUseCase(circle_repo, user_repo)

        with pytest.raises(ValueError, match="already a member"):
            await use_case.execute(
                circle_id=circle.id,
                inviter_id=owner.id,
                invitee_id=invitee.id,
            )


# ── Accept Invite ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAcceptInvite:
    async def test_accept_pending_invite(self) -> None:
        owner = _make_user("alice")
        invitee = _make_user("bob")
        circle = _make_circle(owner.id)
        pending = _make_membership(
            circle.id, invitee.id, invite_status=InviteStatus.PENDING
        )

        circle_repo = AsyncMock()
        circle_repo.get_membership.return_value = pending
        circle_repo.count_members.return_value = 1
        circle_repo.save_membership.return_value = None

        use_case = AcceptInviteUseCase(circle_repo)
        membership = await use_case.execute(circle_id=circle.id, user_id=invitee.id)

        assert membership.invite_status == InviteStatus.ACCEPTED

    async def test_no_invite_raises(self) -> None:
        circle_repo = AsyncMock()
        circle_repo.get_membership.return_value = None

        use_case = AcceptInviteUseCase(circle_repo)

        with pytest.raises(ValueError, match="No pending invitation"):
            await use_case.execute(circle_id=uuid.uuid4(), user_id=uuid.uuid4())


# ── Remove Member ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRemoveMember:
    async def test_self_removal_always_allowed(self) -> None:
        user = _make_user("alice")
        circle_id = uuid.uuid4()
        membership = _make_membership(circle_id, user.id)

        circle_repo = AsyncMock()
        circle_repo.get_membership.return_value = membership
        circle_repo.delete_membership.return_value = None

        use_case = RemoveMemberUseCase(circle_repo)
        await use_case.execute(
            circle_id=circle_id,
            requester_id=user.id,
            target_user_id=user.id,
        )

        circle_repo.delete_membership.assert_called_once()

    async def test_moderator_cannot_remove_owner(self) -> None:
        owner = _make_user("alice")
        moderator = _make_user("bob")
        circle_id = uuid.uuid4()
        owner_membership = _make_membership(circle_id, owner.id, role=CircleRole.OWNER)
        mod_membership = _make_membership(circle_id, moderator.id, role=CircleRole.MODERATOR)

        circle_repo = AsyncMock()
        circle_repo.get_membership.side_effect = lambda cid, uid: (
            owner_membership if uid == owner.id else mod_membership
        )

        use_case = RemoveMemberUseCase(circle_repo)

        with pytest.raises(PermissionError, match="only remove regular members"):
            await use_case.execute(
                circle_id=circle_id,
                requester_id=moderator.id,
                target_user_id=owner.id,
            )

    async def test_owner_can_remove_member(self) -> None:
        owner = _make_user("alice")
        member = _make_user("bob")
        circle_id = uuid.uuid4()
        owner_membership = _make_membership(circle_id, owner.id, role=CircleRole.OWNER)
        member_membership = _make_membership(circle_id, member.id, role=CircleRole.MEMBER)

        circle_repo = AsyncMock()
        circle_repo.get_membership.side_effect = lambda cid, uid: (
            member_membership if uid == member.id else owner_membership
        )
        circle_repo.delete_membership.return_value = None

        use_case = RemoveMemberUseCase(circle_repo)
        await use_case.execute(
            circle_id=circle_id,
            requester_id=owner.id,
            target_user_id=member.id,
        )

        circle_repo.delete_membership.assert_called_once_with(circle_id, member.id)
