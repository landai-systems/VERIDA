# VERIDA Progress Log

This file tracks milestone completions and significant decisions.
Newest entries first.

---

## 2026-07-05 — M2 Core Loop Complete

**By:** automated M2 agent
**Status:** ✅

### What was done

**Database layer:**
- SQLAlchemy async ORM models for all entities: `users`, `posts`, `circles`,
  `circle_memberships`, `daily_moments`, `attestations`, `refresh_tokens`,
  `email_verifications` (all with UUIDv7 PKs and TIMESTAMPTZ columns)
- Alembic migration `0001_initial.py` — creates all tables with proper FK constraints,
  indexes, and unique constraints
- Async session factory with request-scoped session management via FastAPI Depends

**Repository pattern:**
- `SqlUserRepository`, `SqlPostRepository`, `SqlRefreshTokenRepository`,
  `SqlCircleRepository`, `SqlDailyMomentRepository`,
  `SqlEmailVerificationRepository`, `SqlAttestationRepository`
- All implement the corresponding Protocol from `application/ports.py`
- Clean entity↔ORM mapping functions (no ORM leakage into domain layer)

**Application use cases:**
- `InitiateCaptureUseCase` — HMAC-signed capture token (10-min expiry), daily post guard
- `SubmitPostUseCase` — token validation, gallery rejection, EXIF stripping, size limit,
  is_late flag, arq attestation enqueue
- `CreateCircleUseCase`, `InviteMemberUseCase`, `AcceptInviteUseCase`,
  `RemoveMemberUseCase`, `ListCirclesUseCase` — max 30 members enforced
- `GetFeedUseCase` — reciprocity gate + chronological order + pagination
- `SendVerificationEmailUseCase`, `VerifyEmailUseCase`

**API endpoints:**
- `POST /api/v1/capture/initiate` — start capture session, return capture_token
- `POST /api/v1/capture/submit` — submit post with media (multipart)
- `GET /api/v1/feed` — reciprocity-gated, paginated feed
- `GET/DELETE /api/v1/posts/{id}` — read / delete individual posts
- `GET/POST /api/v1/circles` — list / create circles
- `GET/PUT/DELETE /api/v1/circles/{id}` — detail / update / delete circle
- `POST /api/v1/circles/{id}/invite` — invite member
- `POST /api/v1/circles/{id}/accept` — accept invite
- `DELETE /api/v1/circles/{id}/members/{uid}` — remove / leave

**Infrastructure:**
- `MailpitAdapter` (aiosmtplib, dev) + `StubEmailAdapter` (tests)
- `arq` worker: `attest_post`, `send_daily_prompt`, `purge_expired_tokens` tasks
- `WorkerSettings` class for `arq worker verida.infrastructure.worker.WorkerSettings`
- FastAPI `deps.py` — `get_current_user`, session factory deps, repo factories

**Tests (unit, mock-only, no DB required):**
- `test_feed.py` — reciprocity gate, pagination, has_more, empty circles
- `test_circles.py` — CRUD, max 30 enforcement, invite flow, remove/leave
- `test_capture.py` — HMAC token, initiate, submit, gallery rejection, size limit, is_late
- `test_email_verification.py` — send, no-op if verified, verify, expired/used token

### Key decisions

- Capture token: HMAC-SHA256 over `{moment_id}|{user_id}|{unix_ts}` — simple, stateless,
  verifiable without DB round-trip
- Reciprocity gate enforced in use-case layer, not at DB level — easier to test and reason about
- EXIF stripping via Pillow (soft dependency — falls back gracefully if not installed)
- Feed chronological oldest-first; `has_more: false` signals "You're all caught up"
- Max 30 circle members: enforced at application layer (422 if exceeded)
- `is_late: bool` on Post — set when submitted outside the 10-minute capture window
- `gallery` source detection via `capture_metadata.source == "gallery"`
- GDPR: email addresses not logged at INFO level; IPs not collected in application layer
- arq pool is `None` in tests (no Redis) — enqueue is skipped safely
- All ports defined as `@runtime_checkable Protocol` — no adapter leaks into domain

### Not done in M2 (deferred to M3+)

- Frontend pages (login, capture, feed, circles, profile)
- Push notifications for daily prompts (stub only)
- Object storage integration (media_url is a local placeholder for MVP)
- Media upload via presigned S3 URL
- Read/presence indicators
- Reactions and comments

---

## 2026-07-05 — M1 Scaffold Complete

**By:** automated scaffold agent
**Status:** ✅

### What was done

- Created the full M1 repository structure (backend, frontend, docs, CI)
- Implemented auth endpoints: register, login, refresh, logout, /me
- Implemented DO_NOT_DEPLOY guard with automated test coverage
- Created ContentAuthenticityPort Protocol + HeuristicAuthenticityChecker MVP
- Domain entities: User, Post, Circle, DailyMoment, Attestation, RefreshToken
- Frontend PWA shell with React Router routing skeleton
- GitHub Actions CI: ruff, mypy, pytest, bandit, pip-audit, gitleaks, frontend tsc
- Docker Compose: api, db (postgres:16), redis, mailpit, web
- Documentation: ROADMAP, BACKLOG, TRUST_MODEL, PRIVACY, THREAT_MODEL, DATA_MAP,
  ENGAGEMENT, TOMs, ADR 001, ADR 002

### Key decisions

- Argon2id with time_cost=2, memory_cost=64 MiB (OWASP recommended)
- UUIDv7 primary keys via `uuid6` library
- In-memory stores in auth module for M1 — replaced with SQLAlchemy repos in M2
- DO_NOT_DEPLOY guard: RuntimeError on startup if production + no human sign-off
- Clean Architecture strictly enforced: domain has zero external deps

### Not done in M1 (deferred to M2)

- SQLAlchemy models and Alembic migrations
- Real database repositories
- Daily capture flow and media upload
- Circle management endpoints
- Background attestation worker (arq)
- Email verification
- Frontend form pages (login, register, capture)

---

<!-- Add new entries above this line -->
