"""Application port interfaces.

Ports are typed Protocols that the application layer defines and depends on.
Concrete adapters live in ``infrastructure/`` and are injected at runtime.
This keeps the application layer free of infrastructure dependencies
(Clean Architecture dependency rule).

Naming convention
-----------------
  <Capability>Port  — a port that the application layer calls out to
  <Resource>Repository  — a port for reading/writing a domain entity

All methods are async by default; synchronous adapters should wrap
blocking calls in asyncio.to_thread().
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from verida.domain.entities import Attestation, Post

if TYPE_CHECKING:
    from verida.domain.entities import (
        Circle,
        CircleMembership,
        DailyMoment,
        EmailVerification,
        RefreshToken,
        User,
    )


@runtime_checkable
class ContentAuthenticityPort(Protocol):
    """Port for checking whether a piece of content is genuinely human-captured.

    Implementations may use local heuristics (MVP), a remote ML model,
    or a combination.  The application layer only depends on this Protocol;
    it never imports from ``infrastructure``.

    See also: docs/TRUST_MODEL.md for the guarantees (and non-guarantees)
    that any implementation must be honest about.
    """

    async def attest(self, post: Post) -> Attestation:
        """Evaluate a post and return an Attestation result.

        Parameters
        ----------
        post:
            The submitted post with ``media_hash`` and ``capture_metadata``
            populated.

        Returns
        -------
        Attestation:
            An Attestation entity with status and score set.
            Status is one of: PENDING | PASSED | FLAGGED | REJECTED.

        Notes
        -----
        - Implementations MUST be idempotent; calling attest() twice with
          the same post MUST NOT create duplicate side effects.
        - Implementations SHOULD NOT raise; they SHOULD return a FLAGGED
          attestation with ``details`` explaining the reason.
        """
        ...  # Protocol body — never executed


@runtime_checkable
class UserRepository(Protocol):
    """Port for persisting and querying User entities."""

    async def get_by_id(self, user_id: uuid.UUID) -> "User | None":
        ...

    async def get_by_email(self, email: str) -> "User | None":
        ...

    async def get_by_handle(self, handle: str) -> "User | None":
        ...

    async def save(self, user: "User") -> None:
        ...

    async def delete(self, user_id: uuid.UUID) -> None:
        ...


@runtime_checkable
class PostRepository(Protocol):
    """Port for persisting and querying Post entities."""

    async def get_by_id(self, post_id: uuid.UUID) -> Post | None:
        ...

    async def list_by_author(
        self,
        author_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        ...

    async def get_today_post_for_user(
        self,
        user_id: uuid.UUID,
        today: date,
    ) -> "Post | None":
        """Return the post the user made today, if any."""
        ...

    async def list_feed_posts(
        self,
        viewer_id: uuid.UUID,
        circle_ids: list[uuid.UUID],
        today: date,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:
        """Return circle-members' posts from today for the feed."""
        ...

    async def save(self, post: Post) -> None:
        ...

    async def delete(self, post_id: uuid.UUID) -> None:
        ...


@runtime_checkable
class RefreshTokenRepository(Protocol):
    """Port for managing rotating refresh tokens."""

    async def get_by_token_hash(self, token_hash: str) -> "RefreshToken | None":
        ...

    async def save(self, token: "RefreshToken") -> None:
        ...

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        ...

    async def delete_expired(self) -> int:
        """Delete all expired tokens; returns count deleted."""
        ...


@runtime_checkable
class CircleRepository(Protocol):
    """Port for persisting and querying Circle entities."""

    async def get_by_id(self, circle_id: uuid.UUID) -> "Circle | None":
        ...

    async def list_by_owner(self, owner_id: uuid.UUID) -> list["Circle"]:
        ...

    async def list_for_member(self, user_id: uuid.UUID) -> list["Circle"]:
        """Return all circles the user belongs to (any role)."""
        ...

    async def save(self, circle: "Circle") -> None:
        ...

    async def delete(self, circle_id: uuid.UUID) -> None:
        ...

    async def get_membership(
        self, circle_id: uuid.UUID, user_id: uuid.UUID
    ) -> "CircleMembership | None":
        ...

    async def list_members(self, circle_id: uuid.UUID) -> list["CircleMembership"]:
        ...

    async def save_membership(self, membership: "CircleMembership") -> None:
        ...

    async def delete_membership(self, circle_id: uuid.UUID, user_id: uuid.UUID) -> None:
        ...

    async def count_members(self, circle_id: uuid.UUID) -> int:
        """Return the number of accepted members in a circle."""
        ...


@runtime_checkable
class DailyMomentRepository(Protocol):
    """Port for persisting and querying DailyMoment entities."""

    async def get_by_id(self, moment_id: uuid.UUID) -> "DailyMoment | None":
        ...

    async def get_today_for_user(
        self,
        user_id: uuid.UUID,
        today: date,
    ) -> "DailyMoment | None":
        """Return the DailyMoment for the given user and date, if any."""
        ...

    async def save(self, moment: "DailyMoment") -> None:
        ...


@runtime_checkable
class EmailVerificationRepository(Protocol):
    """Port for managing email verification tokens."""

    async def get_by_token_hash(
        self, token_hash: str
    ) -> "EmailVerification | None":
        ...

    async def save(self, verification: "EmailVerification") -> None:
        ...

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        """Remove all pending verification tokens for a user (before re-sending)."""
        ...


@runtime_checkable
class AttestationRepository(Protocol):
    """Port for persisting Attestation entities."""

    async def get_by_post_id(self, post_id: uuid.UUID) -> "Attestation | None":
        ...

    async def save(self, attestation: "Attestation") -> None:
        ...


@runtime_checkable
class EmailPort(Protocol):
    """Port for sending transactional email.

    Implementations may use SMTP (Mailpit in dev), a transactional
    email provider (SES, Postmark) in production, or a stub in tests.
    GDPR constraint: no personal data logged or forwarded to third parties.
    """

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        """Send an email.

        Parameters
        ----------
        to_email:
            Recipient address.  NOT logged at INFO level.
        subject:
            Email subject line.
        body_html:
            HTML body.
        body_text:
            Plain-text fallback body.
        """
        ...
