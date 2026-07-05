"""Use cases for Circle management.

Circles have a max of 30 accepted members (enforced at application layer).
Membership flows:
  1. Owner creates a Circle (owner auto-added as OWNER member).
  2. Owner or Moderator invites a user (invite_status=PENDING).
  3. Invited user accepts or rejects.
  4. Owner or Moderator can remove members.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from verida.application.ports import CircleRepository, UserRepository
from verida.domain.entities import Circle, CircleMembership, CircleRole, InviteStatus

logger = structlog.get_logger(__name__)

MAX_MEMBERS = 30


class CreateCircleUseCase:
    """Create a new Circle and add the creator as OWNER."""

    def __init__(self, circle_repo: CircleRepository) -> None:
        self._repo = circle_repo

    async def execute(
        self,
        owner_id: uuid.UUID,
        name: str,
        description: str = "",
        is_private: bool = True,
    ) -> Circle:
        circle = Circle(
            owner_id=owner_id,
            name=name,
            description=description,
            is_private=is_private,
        )
        await self._repo.save(circle)

        # Auto-add owner as OWNER member (accepted)
        membership = CircleMembership(
            circle_id=circle.id,
            user_id=owner_id,
            role=CircleRole.OWNER,
            invite_status=InviteStatus.ACCEPTED,
        )
        await self._repo.save_membership(membership)

        logger.info("circle_created", circle_id=str(circle.id), owner_id=str(owner_id))
        return circle


class InviteMemberUseCase:
    """Invite a user to a circle (creates a PENDING membership)."""

    def __init__(self, circle_repo: CircleRepository, user_repo: UserRepository) -> None:
        self._circle_repo = circle_repo
        self._user_repo = user_repo

    async def execute(
        self,
        circle_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_id: uuid.UUID,
    ) -> CircleMembership:
        """Invite invitee_id to the circle.

        Raises
        ------
        PermissionError
            If the inviter is not an owner or moderator.
        ValueError
            If the circle is full or the invitee is already a member.
        """
        circle = await self._circle_repo.get_by_id(circle_id)
        if circle is None:
            raise ValueError("Circle not found.")

        inviter_membership = await self._circle_repo.get_membership(circle_id, inviter_id)
        if inviter_membership is None or inviter_membership.role not in (
            CircleRole.OWNER,
            CircleRole.MODERATOR,
        ):
            raise PermissionError("Only circle owners and moderators can invite members.")

        # Check for existing membership
        existing = await self._circle_repo.get_membership(circle_id, invitee_id)
        if existing is not None:
            raise ValueError("This user is already a member or has a pending invite.")

        # Enforce max 30 members
        count = await self._circle_repo.count_members(circle_id)
        if count >= MAX_MEMBERS:
            raise ValueError(
                f"This circle has reached the maximum of {MAX_MEMBERS} members."
            )

        # Verify invitee exists
        invitee = await self._user_repo.get_by_id(invitee_id)
        if invitee is None:
            raise ValueError("Invited user not found.")

        membership = CircleMembership(
            circle_id=circle_id,
            user_id=invitee_id,
            role=CircleRole.MEMBER,
            invite_status=InviteStatus.PENDING,
            invited_by=inviter_id,
        )
        await self._circle_repo.save_membership(membership)

        logger.info(
            "circle_invite_sent",
            circle_id=str(circle_id),
            invitee_id=str(invitee_id),
        )
        return membership


class AcceptInviteUseCase:
    """Accept a pending circle invitation."""

    def __init__(self, circle_repo: CircleRepository) -> None:
        self._repo = circle_repo

    async def execute(self, circle_id: uuid.UUID, user_id: uuid.UUID) -> CircleMembership:
        """Accept the pending invite for user_id in circle_id.

        Raises
        ------
        ValueError
            If there is no pending invite, or the circle is now full.
        """
        membership = await self._repo.get_membership(circle_id, user_id)
        if membership is None or membership.invite_status != InviteStatus.PENDING:
            raise ValueError("No pending invitation found for this circle.")

        # Re-check member count in case the circle filled up after the invite
        count = await self._repo.count_members(circle_id)
        if count >= MAX_MEMBERS:
            raise ValueError(
                f"The circle is now full ({MAX_MEMBERS} members). "
                "Your invitation can no longer be accepted."
            )

        membership.invite_status = InviteStatus.ACCEPTED
        membership.joined_at = datetime.now(UTC)
        await self._repo.save_membership(membership)

        logger.info(
            "circle_invite_accepted",
            circle_id=str(circle_id),
            user_id=str(user_id),
        )
        return membership


class RemoveMemberUseCase:
    """Remove a member from a circle."""

    def __init__(self, circle_repo: CircleRepository) -> None:
        self._repo = circle_repo

    async def execute(
        self,
        circle_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """Remove target_user_id from the circle.

        An OWNER can remove anyone except themselves (transfer ownership first).
        A MODERATOR can remove regular MEMBERs only.
        A user can always remove themselves (leave circle).

        Raises
        ------
        PermissionError
            If the requester lacks permission to remove the target.
        ValueError
            If the target is not a member.
        """
        target_membership = await self._repo.get_membership(circle_id, target_user_id)
        if target_membership is None:
            raise ValueError("Target user is not a member of this circle.")

        # Self-removal is always allowed
        if requester_id == target_user_id:
            await self._repo.delete_membership(circle_id, target_user_id)
            logger.info(
                "circle_member_left",
                circle_id=str(circle_id),
                user_id=str(target_user_id),
            )
            return

        requester_membership = await self._repo.get_membership(circle_id, requester_id)
        if requester_membership is None:
            raise PermissionError("You are not a member of this circle.")

        if requester_membership.role == CircleRole.OWNER:
            if target_membership.role == CircleRole.OWNER:
                raise PermissionError(
                    "Cannot remove another owner. Transfer ownership first."
                )
        elif requester_membership.role == CircleRole.MODERATOR:
            if target_membership.role in (CircleRole.OWNER, CircleRole.MODERATOR):
                raise PermissionError(
                    "Moderators can only remove regular members."
                )
        else:
            raise PermissionError("Only owners and moderators can remove other members.")

        await self._repo.delete_membership(circle_id, target_user_id)

        logger.info(
            "circle_member_removed",
            circle_id=str(circle_id),
            removed_user_id=str(target_user_id),
            by=str(requester_id),
        )


class ListCirclesUseCase:
    """List circles a user belongs to."""

    def __init__(self, circle_repo: CircleRepository) -> None:
        self._repo = circle_repo

    async def execute(self, user_id: uuid.UUID) -> list[Circle]:
        return await self._repo.list_for_member(user_id)
