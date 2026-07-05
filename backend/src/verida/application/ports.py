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
from typing import Protocol, runtime_checkable

from verida.domain.entities import Attestation, Post


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

    async def get_by_id(self, user_id: uuid.UUID) -> "verida.domain.entities.User | None":  # type: ignore[name-defined]
        ...

    async def get_by_email(self, email: str) -> "verida.domain.entities.User | None":  # type: ignore[name-defined]
        ...

    async def get_by_handle(self, handle: str) -> "verida.domain.entities.User | None":  # type: ignore[name-defined]
        ...

    async def save(self, user: "verida.domain.entities.User") -> None:  # type: ignore[name-defined]
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

    async def save(self, post: Post) -> None:
        ...

    async def delete(self, post_id: uuid.UUID) -> None:
        ...


@runtime_checkable
class RefreshTokenRepository(Protocol):
    """Port for managing rotating refresh tokens."""

    async def get_by_token_hash(self, token_hash: str) -> "verida.domain.entities.RefreshToken | None":  # type: ignore[name-defined]
        ...

    async def save(self, token: "verida.domain.entities.RefreshToken") -> None:  # type: ignore[name-defined]
        ...

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        ...
