"""Domain entities — the core business objects of VERIDA.

Design decisions:
- Entities are pure Python dataclasses; they have NO database or framework deps.
- UUIDs use v7 (time-ordered) for efficient B-tree indexing.
- ``uuid6`` provides uuid7() which is monotonically increasing within a
  millisecond, eliminating index fragmentation in PostgreSQL.
- All timestamps are UTC-aware datetimes.
- Validation belongs in application-layer command objects (Pydantic),
  not in entities, to keep the domain dependency-free.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

try:
    from uuid6 import uuid7
except ImportError:  # pragma: no cover — uuid6 installed in production
    import warnings
    warnings.warn("uuid6 not installed; falling back to uuid4", stacklevel=1)
    uuid7 = uuid.uuid4  # type: ignore[assignment]


def _uuid7() -> uuid.UUID:
    """Generate a time-ordered UUID v7."""
    return uuid7()


def _utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


# ── Enumerations ──────────────────────────────────────────────────────────────


class AttestationStatus(str, Enum):
    """Status of a content authenticity attestation."""

    PENDING = "pending"
    PASSED = "passed"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class PostVisibility(str, Enum):
    """Who can see a post."""

    PUBLIC = "public"
    CIRCLES = "circles"  # visible to circles the author belongs to
    PRIVATE = "private"


class CircleRole(str, Enum):
    """A member's role within a Circle."""

    OWNER = "owner"
    MODERATOR = "moderator"
    MEMBER = "member"


# ── Core entities ─────────────────────────────────────────────────────────────


@dataclass
class User:
    """A registered VERIDA user.

    ``handle`` is the unique @-handle displayed in the UI.
    ``email`` is used for login and notifications; it is NOT public.
    ``argon2_hash`` stores the Argon2id password hash.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    handle: str = ""
    email: str = ""
    display_name: str = ""
    argon2_hash: str = ""  # never serialised to API responses
    bio: str = ""
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False  # email verification
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class Circle:
    """A named group of users (friends, family, colleagues …).

    Circles are the primary visibility boundary for posts.
    A user can belong to many circles; a circle has one owner.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    name: str = ""
    description: str = ""
    owner_id: uuid.UUID = field(default_factory=_uuid7)
    is_private: bool = True  # private by default — invite-only
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class CircleMembership:
    """Membership record linking a User to a Circle with a role."""

    id: uuid.UUID = field(default_factory=_uuid7)
    circle_id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    role: CircleRole = CircleRole.MEMBER
    joined_at: datetime = field(default_factory=_utcnow)


@dataclass
class DailyMoment:
    """Metadata about a moment capture session.

    A DailyMoment represents the act of opening the capture window.
    One DailyMoment can have at most one associated Post per day per user.
    The ``capture_token`` is a short-lived token issued by the API when the
    user initiates capture; it is validated when the Post is submitted.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    capture_token: str = ""  # HMAC-signed, expires in 5 minutes
    initiated_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    browser_fingerprint_hash: str = ""  # SHA-256 of client signals, NOT PII


@dataclass
class Attestation:
    """The result of the content authenticity check for a Post.

    IMPORTANT — see docs/TRUST_MODEL.md for what this does and does NOT prove.
    An attestation at PASSED status means the heuristics did not detect
    modification or replay.  It does NOT guarantee that the content is genuine.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    post_id: uuid.UUID = field(default_factory=_uuid7)
    status: AttestationStatus = AttestationStatus.PENDING
    score: float = 0.0  # 0.0 (likely fake) .. 1.0 (likely genuine)
    details: dict[str, object] = field(default_factory=dict)
    checked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Post:
    """A user's daily moment post.

    ``media_hash`` is a SHA-256 of the raw media bytes at the moment of
    capture; it is re-verified during attestation to detect post-upload
    modification.
    ``capture_metadata`` stores browser-reported signals (resolution, duration,
    MIME type).  It is used by the authenticity heuristics and is NOT shown
    to other users.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    author_id: uuid.UUID = field(default_factory=_uuid7)
    daily_moment_id: uuid.UUID = field(default_factory=_uuid7)
    caption: str = ""
    media_url: str = ""       # CDN / object storage URL
    media_hash: str = ""      # SHA-256 of raw media bytes
    media_mime_type: str = ""
    visibility: PostVisibility = PostVisibility.CIRCLES
    attestation: Optional[Attestation] = None
    capture_metadata: dict[str, object] = field(default_factory=dict)
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class RefreshToken:
    """A rotating refresh token stored server-side.

    The token value is a cryptographically random string.  Only the most
    recent token per user is valid (rotation invalidates the previous one).
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    token_hash: str = ""  # SHA-256 of the raw token — never stored plain
    expires_at: datetime = field(default_factory=_utcnow)
    revoked: bool = False
    created_at: datetime = field(default_factory=_utcnow)
