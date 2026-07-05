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
from datetime import UTC, date, datetime
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


class InviteStatus(str, Enum):
    """Status of a circle membership invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ConsentType(str, Enum):
    """Types of consent that VERIDA requests."""

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"


class ReactionEmoji(str, Enum):
    """Allowed reaction emoji — warm, limited, non-competitive set.

    No counts are shown publicly (MVP). Only the current user's own
    reactions are returned in API responses.
    """

    HEART = "\u2764\ufe0f"     # ❤️
    SMILE = "\U0001f60a"       # 😊
    FIRE = "\U0001f525"        # 🔥
    STAR = "\U0001f31f"        # 🌟
    HUG = "\U0001f917"         # 🤗


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
    invite_status: InviteStatus = InviteStatus.ACCEPTED
    invited_by: Optional[uuid.UUID] = None
    joined_at: datetime = field(default_factory=_utcnow)


@dataclass
class DailyMoment:
    """Metadata about a moment capture session.

    A DailyMoment represents the act of opening the capture window.
    One DailyMoment can have at most one associated Post per day per user.
    The ``capture_token`` is a short-lived HMAC-signed token issued by the API
    when the user initiates capture; it is validated when the Post is submitted.
    The capture window is 10 minutes; posts submitted after this are marked late.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    capture_token: str = ""  # HMAC-signed, expires in 10 minutes
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
    ``is_late`` is True if the post was submitted after the 10-minute capture
    window defined by the associated DailyMoment.
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
    is_late: bool = False     # True if submitted after 10-minute capture window
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


@dataclass
class EmailVerification:
    """An email verification token sent to a user.

    The token is a short-lived random string; only its SHA-256 hash is stored.
    On successful verification, ``used_at`` is set and the User is marked verified.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    token_hash: str = ""      # SHA-256 of raw token — never stored plain
    expires_at: datetime = field(default_factory=_utcnow)
    used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)


# ── M3 entities ───────────────────────────────────────────────────────────────


@dataclass
class ConsentRecord:
    """A versioned consent record for a user.

    GDPR requires that consent be freely given, specific, informed, and
    unambiguous.  We store:
    - ``consent_type``: which type of processing the user consented to
    - ``version``: semantic version of the consent text shown (e.g. "1.0")
    - ``text_version``: SHA-256 of the exact consent text shown to the user
    - ``ip_hash``: truncated to /24 prefix — NOT a full IP address
    - ``granted_at``: when consent was given; None means it was withdrawn
    - ``withdrawn_at``: when consent was withdrawn (if applicable)

    Consent records are append-only; withdrawal adds a new record with
    ``withdrawn_at`` set rather than deleting the grant record.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    consent_type: ConsentType = ConsentType.TERMS_OF_SERVICE
    version: str = "1.0"
    text_version: str = ""    # SHA-256 of consent text shown — proof of what user saw
    granted_at: datetime = field(default_factory=_utcnow)
    withdrawn_at: Optional[datetime] = None
    ip_hash: str = ""         # /24-truncated IP, hashed — never the full address
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Reaction:
    """A user's reaction to a post.

    MVP constraints (see docs/ENGAGEMENT.md):
    - Only one reaction of each type per user per post (unique constraint)
    - NO public reaction counters — only whether the current user reacted
    - Warm emoji set only — no thumbs down, no negative reactions
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    post_id: uuid.UUID = field(default_factory=_uuid7)
    user_id: uuid.UUID = field(default_factory=_uuid7)
    emoji: ReactionEmoji = ReactionEmoji.HEART
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Comment:
    """A plain-text comment on a post.

    Body is limited to 500 characters (enforced at both API and DB layers).
    No rich text, no markdown, no mentions in MVP.
    """

    id: uuid.UUID = field(default_factory=_uuid7)
    post_id: uuid.UUID = field(default_factory=_uuid7)
    author_id: uuid.UUID = field(default_factory=_uuid7)
    body: str = ""            # plain-text, max 500 chars
    created_at: datetime = field(default_factory=_utcnow)
    deleted_at: Optional[datetime] = None  # soft-delete for author/mod


@dataclass
class UserStreak:
    """Streak tracking for a user's daily posting habit.

    Grace-day semantics (see docs/ENGAGEMENT.md):
    - A user may miss up to 2 days per calendar month without losing their streak.
    - ``grace_days_used_this_month`` resets on the 1st of each month.
    - NO red-dot badge spam, NO guilt-trip copy — streaks are positive only.
    - ``last_post_date`` is the calendar date (UTC) of the most recent post.
    """

    user_id: uuid.UUID = field(default_factory=_uuid7)
    current_streak: int = 0
    longest_streak: int = 0
    grace_days_used_this_month: int = 0
    last_post_date: Optional[date] = None
    grace_month: Optional[str] = None   # "YYYY-MM" — tracks which month grace applies to
    updated_at: datetime = field(default_factory=_utcnow)
