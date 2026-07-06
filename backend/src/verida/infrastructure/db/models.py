"""SQLAlchemy ORM models for all VERIDA entities.

Design notes:
- All tables use UUIDv7 primary keys (stored as UUID natively in PostgreSQL).
- All timestamps are stored as TIMESTAMPTZ (timezone-aware).
- JSONB columns are used for flexible metadata (capture_metadata, attestation details).
- No ``__repr__`` with sensitive fields — prevents accidental log leaks.
- ``mapped_column(init=False, ...)`` so dataclass-style constructors remain clean.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import JSON as _SAJSON


# Use JSONB on PostgreSQL, JSON on other databases (e.g. SQLite for tests)
def _json_col() -> JSONB:
    """Return JSONB for PostgreSQL, plain JSON for other dialects."""
    return JSONB().with_variant(_SAJSON(), "sqlite")


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    handle: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    argon2_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # relationships
    posts: Mapped[list["PostModel"]] = relationship(back_populates="author", lazy="noload")
    circles_owned: Mapped[list["CircleModel"]] = relationship(
        back_populates="owner", lazy="noload"
    )
    memberships: Mapped[list["CircleMembershipModel"]] = relationship(
        back_populates="user", foreign_keys="CircleMembershipModel.user_id", lazy="noload"
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        back_populates="user", lazy="noload"
    )
    daily_moments: Mapped[list["DailyMomentModel"]] = relationship(
        back_populates="user", lazy="noload"
    )
    email_verifications: Mapped[list["EmailVerificationModel"]] = relationship(
        back_populates="user", lazy="noload"
    )
    consent_records: Mapped[list["ConsentRecordModel"]] = relationship(
        back_populates="user", lazy="noload"
    )
    comments: Mapped[list["CommentModel"]] = relationship(
        back_populates="author", lazy="noload"
    )
    reactions: Mapped[list["ReactionModel"]] = relationship(
        back_populates="user", lazy="noload"
    )
    streak: Mapped[Optional["UserStreakModel"]] = relationship(
        back_populates="user", lazy="noload", uselist=False
    )


class CircleModel(Base):
    __tablename__ = "circles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["UserModel"] = relationship(back_populates="circles_owned", lazy="noload")
    memberships: Mapped[list["CircleMembershipModel"]] = relationship(
        back_populates="circle", lazy="noload"
    )


class CircleMembershipModel(Base):
    __tablename__ = "circle_memberships"
    __table_args__ = (
        UniqueConstraint("circle_id", "user_id", name="uq_circle_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    circle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("circles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    invite_status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    circle: Mapped["CircleModel"] = relationship(back_populates="memberships", lazy="noload")
    user: Mapped["UserModel"] = relationship(
        back_populates="memberships", foreign_keys=[user_id], lazy="noload"
    )


class DailyMomentModel(Base):
    __tablename__ = "daily_moments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capture_token: Mapped[str] = mapped_column(String(512), nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    browser_fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    user: Mapped["UserModel"] = relationship(back_populates="daily_moments", lazy="noload")
    post: Mapped[Optional["PostModel"]] = relationship(
        back_populates="daily_moment", lazy="noload"
    )


class AttestationModel(Base):
    __tablename__ = "attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    details: Mapped[dict] = mapped_column(_json_col(), nullable=False, default=dict)
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped["PostModel"] = relationship(back_populates="attestation_model", lazy="noload")


class PostModel(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    daily_moment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_moments.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    media_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    media_mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="circles")
    capture_metadata: Mapped[dict] = mapped_column(_json_col(), nullable=False, default=dict)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    author: Mapped["UserModel"] = relationship(back_populates="posts", lazy="noload")
    daily_moment: Mapped["DailyMomentModel"] = relationship(
        back_populates="post", lazy="noload"
    )
    attestation_model: Mapped[Optional["AttestationModel"]] = relationship(
        back_populates="post", lazy="noload"
    )
    comments: Mapped[list["CommentModel"]] = relationship(
        back_populates="post", lazy="noload"
    )
    reactions: Mapped[list["ReactionModel"]] = relationship(
        back_populates="post", lazy="noload"
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(back_populates="refresh_tokens", lazy="noload")


class EmailVerificationModel(Base):
    __tablename__ = "email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(back_populates="email_verifications", lazy="noload")


# ── M3 models ─────────────────────────────────────────────────────────────────


class ConsentRecordModel(Base):
    """Append-only consent record. Never UPDATE; only INSERT new rows.

    The ``withdrawn_at`` field is the exception — it's set on withdrawal
    rather than creating a new deletion record.
    """
    __tablename__ = "consent_records"
    __table_args__ = (
        # Index for fast lookup of user's active consent
        {"comment": "Versioned consent records — append-only audit log"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    text_version: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of consent text
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(back_populates="consent_records", lazy="noload")


class ReactionModel(Base):
    """User reaction to a post. One emoji per user per post (unique constraint)."""
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", "emoji", name="uq_reaction_post_user_emoji"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    emoji: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped["PostModel"] = relationship(back_populates="reactions", lazy="noload")
    user: Mapped["UserModel"] = relationship(back_populates="reactions", lazy="noload")


class CommentModel(Base):
    """Plain-text comment on a post. Max 500 chars. Soft-deletable."""
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    post: Mapped["PostModel"] = relationship(back_populates="comments", lazy="noload")
    author: Mapped["UserModel"] = relationship(back_populates="comments", lazy="noload")


class UserStreakModel(Base):
    """Streak tracking — one row per user (upsert pattern)."""
    __tablename__ = "user_streaks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grace_days_used_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_post_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    grace_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # YYYY-MM
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["UserModel"] = relationship(back_populates="streak", lazy="noload")
