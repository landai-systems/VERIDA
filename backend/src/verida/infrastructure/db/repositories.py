"""Concrete repository implementations backed by SQLAlchemy async sessions.

Each class implements the corresponding Protocol from ``application/ports.py``.
All repositories receive an ``AsyncSession`` via constructor injection —
they do NOT create sessions themselves.

Mapping strategy: ORM models ↔ domain entities are converted via thin
``_to_entity`` / ``_from_entity`` helper functions to keep ORM concerns out
of the domain layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from verida.domain.entities import (
    Attestation,
    AttestationStatus,
    Circle,
    CircleMembership,
    CircleRole,
    DailyMoment,
    EmailVerification,
    InviteStatus,
    Post,
    PostVisibility,
    RefreshToken,
    User,
)
from verida.infrastructure.db.models import (
    AttestationModel,
    CircleMembershipModel,
    CircleModel,
    DailyMomentModel,
    EmailVerificationModel,
    PostModel,
    RefreshTokenModel,
    UserModel,
)


# ── Mapping helpers ────────────────────────────────────────────────────────────

def _user_to_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        handle=m.handle,
        email=m.email,
        display_name=m.display_name,
        argon2_hash=m.argon2_hash,
        bio=m.bio,
        avatar_url=m.avatar_url,
        is_active=m.is_active,
        is_verified=m.is_verified,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _user_from_entity(u: User) -> UserModel:
    return UserModel(
        id=u.id,
        handle=u.handle,
        email=u.email,
        display_name=u.display_name,
        argon2_hash=u.argon2_hash,
        bio=u.bio,
        avatar_url=u.avatar_url,
        is_active=u.is_active,
        is_verified=u.is_verified,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


def _post_to_entity(m: PostModel, attestation_m: Optional[AttestationModel] = None) -> Post:
    att: Optional[Attestation] = None
    if attestation_m:
        att = Attestation(
            id=attestation_m.id,
            post_id=attestation_m.post_id,
            status=AttestationStatus(attestation_m.status),
            score=attestation_m.score,
            details=attestation_m.details,
            checked_at=attestation_m.checked_at,
            created_at=attestation_m.created_at,
        )
    return Post(
        id=m.id,
        author_id=m.author_id,
        daily_moment_id=m.daily_moment_id,
        caption=m.caption,
        media_url=m.media_url,
        media_hash=m.media_hash,
        media_mime_type=m.media_mime_type,
        visibility=PostVisibility(m.visibility),
        attestation=att,
        capture_metadata=m.capture_metadata,
        is_late=m.is_late,
        published_at=m.published_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _post_from_entity(p: Post) -> PostModel:
    return PostModel(
        id=p.id,
        author_id=p.author_id,
        daily_moment_id=p.daily_moment_id,
        caption=p.caption,
        media_url=p.media_url,
        media_hash=p.media_hash,
        media_mime_type=p.media_mime_type,
        visibility=p.visibility.value,
        capture_metadata=p.capture_metadata,
        is_late=p.is_late,
        published_at=p.published_at,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _circle_to_entity(m: CircleModel) -> Circle:
    return Circle(
        id=m.id,
        name=m.name,
        description=m.description,
        owner_id=m.owner_id,
        is_private=m.is_private,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _circle_from_entity(c: Circle) -> CircleModel:
    return CircleModel(
        id=c.id,
        name=c.name,
        description=c.description,
        owner_id=c.owner_id,
        is_private=c.is_private,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _membership_to_entity(m: CircleMembershipModel) -> CircleMembership:
    return CircleMembership(
        id=m.id,
        circle_id=m.circle_id,
        user_id=m.user_id,
        role=CircleRole(m.role),
        invite_status=InviteStatus(m.invite_status),
        invited_by=m.invited_by,
        joined_at=m.joined_at,
    )


def _membership_from_entity(m: CircleMembership) -> CircleMembershipModel:
    return CircleMembershipModel(
        id=m.id,
        circle_id=m.circle_id,
        user_id=m.user_id,
        role=m.role.value,
        invite_status=m.invite_status.value,
        invited_by=m.invited_by,
        joined_at=m.joined_at,
    )


def _daily_moment_to_entity(m: DailyMomentModel) -> DailyMoment:
    return DailyMoment(
        id=m.id,
        user_id=m.user_id,
        capture_token=m.capture_token,
        initiated_at=m.initiated_at,
        completed_at=m.completed_at,
        browser_fingerprint_hash=m.browser_fingerprint_hash,
    )


def _daily_moment_from_entity(d: DailyMoment) -> DailyMomentModel:
    return DailyMomentModel(
        id=d.id,
        user_id=d.user_id,
        capture_token=d.capture_token,
        initiated_at=d.initiated_at,
        completed_at=d.completed_at,
        browser_fingerprint_hash=d.browser_fingerprint_hash,
    )


def _refresh_token_to_entity(m: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        expires_at=m.expires_at,
        revoked=m.revoked,
        created_at=m.created_at,
    )


def _refresh_token_from_entity(r: RefreshToken) -> RefreshTokenModel:
    return RefreshTokenModel(
        id=r.id,
        user_id=r.user_id,
        token_hash=r.token_hash,
        expires_at=r.expires_at,
        revoked=r.revoked,
        created_at=r.created_at,
    )


def _email_verification_to_entity(m: EmailVerificationModel) -> EmailVerification:
    return EmailVerification(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        expires_at=m.expires_at,
        used_at=m.used_at,
        created_at=m.created_at,
    )


def _email_verification_from_entity(e: EmailVerification) -> EmailVerificationModel:
    return EmailVerificationModel(
        id=e.id,
        user_id=e.user_id,
        token_hash=e.token_hash,
        expires_at=e.expires_at,
        used_at=e.used_at,
        created_at=e.created_at,
    )


def _attestation_to_entity(m: AttestationModel) -> Attestation:
    return Attestation(
        id=m.id,
        post_id=m.post_id,
        status=AttestationStatus(m.status),
        score=m.score,
        details=m.details,
        checked_at=m.checked_at,
        created_at=m.created_at,
    )


def _attestation_from_entity(a: Attestation) -> AttestationModel:
    return AttestationModel(
        id=a.id,
        post_id=a.post_id,
        status=a.status.value,
        score=a.score,
        details=a.details,
        checked_at=a.checked_at,
        created_at=a.created_at,
    )


# ── Repository implementations ─────────────────────────────────────────────────


class SqlUserRepository:
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.get(UserModel, user_id)
        return _user_to_entity(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.scalar(stmt)
        return _user_to_entity(result) if result else None

    async def get_by_handle(self, handle: str) -> User | None:
        stmt = select(UserModel).where(UserModel.handle == handle)
        result = await self._session.scalar(stmt)
        return _user_to_entity(result) if result else None

    async def save(self, user: User) -> None:
        existing = await self._session.get(UserModel, user.id)
        if existing:
            existing.handle = user.handle
            existing.email = user.email
            existing.display_name = user.display_name
            existing.argon2_hash = user.argon2_hash
            existing.bio = user.bio
            existing.avatar_url = user.avatar_url
            existing.is_active = user.is_active
            existing.is_verified = user.is_verified
            existing.updated_at = user.updated_at
        else:
            self._session.add(_user_from_entity(user))

    async def delete(self, user_id: uuid.UUID) -> None:
        existing = await self._session.get(UserModel, user_id)
        if existing:
            await self._session.delete(existing)


class SqlPostRepository:
    """SQLAlchemy implementation of PostRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, post_id: uuid.UUID) -> Post | None:
        post_m = await self._session.get(PostModel, post_id)
        if not post_m:
            return None
        att_m = await self._session.scalar(
            select(AttestationModel).where(AttestationModel.post_id == post_id)
        )
        return _post_to_entity(post_m, att_m)

    async def list_by_author(
        self,
        author_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        stmt = (
            select(PostModel)
            .where(PostModel.author_id == author_id)
            .order_by(PostModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_post_to_entity(row) for row in rows]

    async def get_today_post_for_user(
        self,
        user_id: uuid.UUID,
        today: date,
    ) -> Post | None:
        start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        end = datetime(today.year, today.month, today.day, 23, 59, 59, 999999, tzinfo=UTC)
        stmt = select(PostModel).where(
            and_(
                PostModel.author_id == user_id,
                PostModel.created_at >= start,
                PostModel.created_at <= end,
            )
        )
        row = await self._session.scalar(stmt)
        return _post_to_entity(row) if row else None

    async def list_feed_posts(
        self,
        viewer_id: uuid.UUID,
        circle_ids: list[uuid.UUID],
        today: date,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        """Return posts from today by users in the viewer's circles (feed)."""
        if not circle_ids:
            return []

        start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        end = datetime(today.year, today.month, today.day, 23, 59, 59, 999999, tzinfo=UTC)

        # Sub-query: find author_ids who are members of the viewer's circles
        member_ids_stmt = (
            select(CircleMembershipModel.user_id)
            .where(
                and_(
                    CircleMembershipModel.circle_id.in_(circle_ids),
                    CircleMembershipModel.invite_status == "accepted",
                    CircleMembershipModel.user_id != viewer_id,
                )
            )
            .distinct()
        )

        stmt = (
            select(PostModel)
            .where(
                and_(
                    PostModel.author_id.in_(member_ids_stmt),
                    PostModel.created_at >= start,
                    PostModel.created_at <= end,
                    PostModel.visibility.in_(["circles", "public"]),
                )
            )
            .order_by(PostModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_post_to_entity(row) for row in rows]

    async def save(self, post: Post) -> None:
        existing = await self._session.get(PostModel, post.id)
        if existing:
            existing.caption = post.caption
            existing.media_url = post.media_url
            existing.media_hash = post.media_hash
            existing.media_mime_type = post.media_mime_type
            existing.visibility = post.visibility.value
            existing.capture_metadata = post.capture_metadata
            existing.is_late = post.is_late
            existing.published_at = post.published_at
            existing.updated_at = post.updated_at
        else:
            self._session.add(_post_from_entity(post))

    async def delete(self, post_id: uuid.UUID) -> None:
        existing = await self._session.get(PostModel, post_id)
        if existing:
            await self._session.delete(existing)


class SqlRefreshTokenRepository:
    """SQLAlchemy implementation of RefreshTokenRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.scalar(stmt)
        return _refresh_token_to_entity(result) if result else None

    async def save(self, token: RefreshToken) -> None:
        existing = await self._session.get(RefreshTokenModel, token.id)
        if existing:
            existing.revoked = token.revoked
            existing.expires_at = token.expires_at
        else:
            self._session.add(_refresh_token_from_entity(token))

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .values(revoked=True)
        )
        await self._session.execute(stmt)

    async def delete_expired(self) -> int:
        now = datetime.now(UTC)
        stmt = delete(RefreshTokenModel).where(RefreshTokenModel.expires_at < now)
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]


class SqlCircleRepository:
    """SQLAlchemy implementation of CircleRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, circle_id: uuid.UUID) -> Circle | None:
        result = await self._session.get(CircleModel, circle_id)
        return _circle_to_entity(result) if result else None

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Circle]:
        stmt = select(CircleModel).where(CircleModel.owner_id == owner_id)
        rows = (await self._session.scalars(stmt)).all()
        return [_circle_to_entity(row) for row in rows]

    async def list_for_member(self, user_id: uuid.UUID) -> list[Circle]:
        stmt = (
            select(CircleModel)
            .join(
                CircleMembershipModel,
                and_(
                    CircleMembershipModel.circle_id == CircleModel.id,
                    CircleMembershipModel.user_id == user_id,
                    CircleMembershipModel.invite_status == "accepted",
                ),
            )
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_circle_to_entity(row) for row in rows]

    async def save(self, circle: Circle) -> None:
        existing = await self._session.get(CircleModel, circle.id)
        if existing:
            existing.name = circle.name
            existing.description = circle.description
            existing.is_private = circle.is_private
            existing.updated_at = circle.updated_at
        else:
            self._session.add(_circle_from_entity(circle))

    async def delete(self, circle_id: uuid.UUID) -> None:
        existing = await self._session.get(CircleModel, circle_id)
        if existing:
            await self._session.delete(existing)

    async def get_membership(
        self, circle_id: uuid.UUID, user_id: uuid.UUID
    ) -> CircleMembership | None:
        stmt = select(CircleMembershipModel).where(
            and_(
                CircleMembershipModel.circle_id == circle_id,
                CircleMembershipModel.user_id == user_id,
            )
        )
        result = await self._session.scalar(stmt)
        return _membership_to_entity(result) if result else None

    async def list_members(self, circle_id: uuid.UUID) -> list[CircleMembership]:
        stmt = select(CircleMembershipModel).where(
            CircleMembershipModel.circle_id == circle_id
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_membership_to_entity(row) for row in rows]

    async def save_membership(self, membership: CircleMembership) -> None:
        stmt = select(CircleMembershipModel).where(
            and_(
                CircleMembershipModel.circle_id == membership.circle_id,
                CircleMembershipModel.user_id == membership.user_id,
            )
        )
        existing = await self._session.scalar(stmt)
        if existing:
            existing.role = membership.role.value
            existing.invite_status = membership.invite_status.value
            existing.joined_at = membership.joined_at
        else:
            self._session.add(_membership_from_entity(membership))

    async def delete_membership(self, circle_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = delete(CircleMembershipModel).where(
            and_(
                CircleMembershipModel.circle_id == circle_id,
                CircleMembershipModel.user_id == user_id,
            )
        )
        await self._session.execute(stmt)

    async def count_members(self, circle_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            and_(
                CircleMembershipModel.circle_id == circle_id,
                CircleMembershipModel.invite_status == "accepted",
            )
        )
        result = await self._session.scalar(stmt)
        return result or 0


class SqlDailyMomentRepository:
    """SQLAlchemy implementation of DailyMomentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, moment_id: uuid.UUID) -> DailyMoment | None:
        result = await self._session.get(DailyMomentModel, moment_id)
        return _daily_moment_to_entity(result) if result else None

    async def get_today_for_user(
        self,
        user_id: uuid.UUID,
        today: date,
    ) -> DailyMoment | None:
        start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        end = datetime(today.year, today.month, today.day, 23, 59, 59, 999999, tzinfo=UTC)
        stmt = select(DailyMomentModel).where(
            and_(
                DailyMomentModel.user_id == user_id,
                DailyMomentModel.initiated_at >= start,
                DailyMomentModel.initiated_at <= end,
            )
        )
        result = await self._session.scalar(stmt)
        return _daily_moment_to_entity(result) if result else None

    async def save(self, moment: DailyMoment) -> None:
        existing = await self._session.get(DailyMomentModel, moment.id)
        if existing:
            existing.capture_token = moment.capture_token
            existing.completed_at = moment.completed_at
            existing.browser_fingerprint_hash = moment.browser_fingerprint_hash
        else:
            self._session.add(_daily_moment_from_entity(moment))


class SqlEmailVerificationRepository:
    """SQLAlchemy implementation of EmailVerificationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> EmailVerification | None:
        stmt = select(EmailVerificationModel).where(
            EmailVerificationModel.token_hash == token_hash
        )
        result = await self._session.scalar(stmt)
        return _email_verification_to_entity(result) if result else None

    async def save(self, verification: EmailVerification) -> None:
        existing = await self._session.get(EmailVerificationModel, verification.id)
        if existing:
            existing.used_at = verification.used_at
        else:
            self._session.add(_email_verification_from_entity(verification))

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        stmt = delete(EmailVerificationModel).where(
            EmailVerificationModel.user_id == user_id
        )
        await self._session.execute(stmt)


class SqlAttestationRepository:
    """SQLAlchemy implementation of AttestationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_post_id(self, post_id: uuid.UUID) -> Attestation | None:
        stmt = select(AttestationModel).where(AttestationModel.post_id == post_id)
        result = await self._session.scalar(stmt)
        return _attestation_to_entity(result) if result else None

    async def save(self, attestation: Attestation) -> None:
        existing = await self._session.scalar(
            select(AttestationModel).where(AttestationModel.post_id == attestation.post_id)
        )
        if existing:
            existing.status = attestation.status.value
            existing.score = attestation.score
            existing.details = attestation.details
            existing.checked_at = attestation.checked_at
        else:
            self._session.add(_attestation_from_entity(attestation))
