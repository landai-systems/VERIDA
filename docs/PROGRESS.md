# VERIDA Progress Log

This file tracks milestone completions and significant decisions.
Newest entries first.

---

## 2026-07-05 — M3 Trust & Compliance Complete

**By:** automated M3 agent  
**Status:** ✅

### What was done

**Authenticity upgrades:**
- `HeuristicAuthenticityChecker` extended with 9 heuristics (from 5): added
  perceptual-hash replay detection (Redis), timing-window validation, EXIF absence
  check, capture metadata completeness scoring, gallery-upload detection
- `AttestationUseCase` — new orchestrator use case for attesting posts
- arq `attest_post` worker now passes Redis client for phash dedup

**Consent management (GDPR Art. 7):**
- New `ConsentRecord` entity (user_id, consent_type, version, text_version, ip_hash)
- `ConsentRecordModel` + `SqlConsentRepository`
- `RecordConsentUseCase`, `GetConsentHistoryUseCase`, `WithdrawConsentUseCase`
- `POST /api/v1/consent`, `GET /api/v1/consent`, `POST /api/v1/consent/withdraw`
- Consent records are append-only (audit trail); withdrawal sets `withdrawn_at`, never deletes
- `text_version` = SHA-256 of the exact consent text shown — proof of what user agreed to
- IP hashed as /24 prefix only — no full IP stored

**GDPR data portability + erasure:**
- `ExportUserDataUseCase` — collects all user data (profile, posts, circles, comments,
  reactions, consent records, streak) into structured JSON (no argon2_hash exported)
- `DeleteUserDataUseCase` — hard delete with cascade + schedules `purge_deleted_user_data` arq job
- `POST /api/v1/gdpr/export` — returns JSON file download
- `DELETE /api/v1/gdpr/me` — requires `{"confirm": "DELETE MY ACCOUNT"}` to prevent accidents
- `purge_deleted_user_data` arq task added to `WorkerSettings`

**Rate limiting:**
- `SlidingWindowRateLimiter` — Redis sorted-set sliding window, generic error messages (no user enumeration)
- `@rate_limit(requests, window_seconds, key_prefix)` decorator for route handlers
- IP truncated to /24 for rate-limit keys

**Security headers:**
- `SecurityHeadersMiddleware` — added to app startup
- Headers: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP (no unsafe-inline), Permissions-Policy
- CSP: camera/microphone `self` (needed for capture), geolocation explicitly blocked

**Reactions:**
- `Reaction` entity + `ReactionModel` (unique constraint: one emoji per user per post)
- `SqlReactionRepository`
- `AddReactionUseCase` (idempotent), `RemoveReactionUseCase`, `GetReactionsUseCase`
- `POST/DELETE /api/v1/posts/{id}/reactions` — NO public counters, only user's own reactions
- Warm emoji set: ❤️ 😊 🔥 🌟 🤗 (no negative reactions)

**Comments:**
- `Comment` entity + `CommentModel` (body: String(500), soft-delete via deleted_at)
- `SqlCommentRepository`
- `AddCommentUseCase`, `DeleteCommentUseCase`, `ListCommentsUseCase`
- `GET/POST /api/v1/posts/{id}/comments`, `DELETE /api/v1/posts/{id}/comments/{id}`
- Plain-text only, max 500 chars, author-deletable

**Streaks:**
- `UserStreak` entity + `UserStreakModel` + `SqlStreakRepository`
- `UpdateStreakUseCase` — grace days (max 2/month), monthly reset, NO guilt copy
- `GetStreakUseCase`
- `GET /api/v1/me/streak` — returns current/longest streak, NO countdown messaging

**Database migration:**
- Alembic `0002_consent_reactions_comments_streaks.py`

**Documentation:**
- `PRIVACY.md` — complete: consent flows, retention schedules, Art. 17/20 implementation, German summary
- `DATA_MAP.md` — ConsentRecord, Reaction, Comment, Streak added
- `THREAT_MODEL.md` — STRIDE updated with M3 attack surfaces
- `ENGAGEMENT.md` — streak mechanics, grace-day rationale, ethical principles
- `TRUST_MODEL.md` — upgraded heuristics documented with honest limits
- `BACKLOG.md` — M3 items marked ✅ Done
- `docs/adr/003-consent-model.md` — ADR for versioned consent

**Tests (unit, mock-only, no DB required):**
- `test_consent.py` — record, history, withdraw, text_version hashing, append-only
- `test_gdpr.py` — export completeness, cascade delete, purge job scheduling
- `test_reactions.py` — add, remove, idempotent, NO public counters enforced
- `test_comments.py` — add, delete, length limit, list excludes deleted
- `test_streaks.py` — increment, grace days, monthly reset, longest tracking

### Key decisions

- Consent records are **append-only**: withdrawal adds `withdrawn_at`, never deletes.
  This preserves the Art. 5(2) accountability audit trail.
- Reaction counters are **private**: `GetReactionsUseCase` returns only the current user's
  reactions. Public counts create competition; the spec forbids them in MVP.
- Streaks are **positive-only**: API response omits countdown/deadline fields.
  See `docs/ENGAGEMENT.md` for ethical rationale.
- Rate-limit errors use **generic messages** — "Too many requests" only, never "email not found".
  This prevents user enumeration via timing/response.
- IP addresses are truncated to **/24 prefix** before hashing in both rate-limit keys and
  consent records. Full IPs are never stored.
- CSP forbids `unsafe-inline` — required for M3 security hardening.
- GDPR erasure requires explicit confirmation string `"DELETE MY ACCOUNT"` to prevent
  accidental account deletion.

### Not done in M3 (deferred to M4+)

- Frontend integration (reactions UI, comment threads, streak display)
- Push notifications for daily prompts
- Media purge from object storage (purge worker stub only in MVP)
- Admin moderation dashboard
- Email digest notifications

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

## 2026-07-05 — M4 Polish & Demo Complete

**By:** automated M4 agent  
**Status:** ✅

### What was done

**Frontend UI (complete — React 18 + TypeScript + Vite + Tailwind):**
- `App.tsx` — React Router v6, lazy-loaded pages, RequireAuth guard, ErrorBoundary
- Pages: LoginPage, RegisterPage, CapturePage, FeedPage, CirclesPage, ProfilePage, ArchivePage, SettingsPage
- Components: Layout (bottom nav), PostCard (attestation badge, reactions, comments), CameraCapture (getUserMedia, permission fallback, text mode), ReactionBar (5 emoji, no counters), CommentSection (500 char limit), AttestationBadge (✓/⚠/⏳), StreakBadge (🔥 N, no deadline), EmptyState (inline SVG), ErrorBoundary (graceful), SessionNudge (10 min modal)
- API client (axios, JWT auto-attach, auto-refresh on 401, queue-based retry)
- Zustand stores: `authStore` (persist, login/logout/register/restoreSession) + `feedStore` (posts, pagination, hasMomentToday, optimistic reactions)
- PWA: manifest.json complete + Workbox service worker via vite-plugin-pwa

**UX features:**
- Reciprocity gate: "Post your moment first" if no moment today
- Session nudge: modal after 10 min continuous use ("Take a break? 🌿")
- "You're all caught up" 🌿 end-of-feed marker + infinite scroll via IntersectionObserver
- Archive grid: monthly grouping of personal posts
- Dark/light mode (Tailwind prefers-color-scheme + dark: variants)
- Accessibility: ARIA labels, roles, aria-live, aria-pressed on all interactive elements

**Seed script (`scripts/seed.py`):**
- Faker(seed=42) — fully deterministic, same data every run
- Creates: 10 users, 3 circles with memberships, 30 posts (past 30 days), 20 reactions, 15 comments, 2 consent records/user, streaks
- All posts have attestation status=passed
- Uses picsum.photos for placeholder media, pravatar.cc for avatars
- Prints: "Seeded: 10 users, 30 posts, 3 circles"

**Docker:**
- `backend/Dockerfile` — multi-stage (builder + final), non-root user, uvicorn
- `frontend/Dockerfile.dev` — node:20-alpine, `--host 0.0.0.0` for Docker exposure

**Docs:**
- `docs/DEMO.md` — 12-step demo script with talking points and screenshot placeholders
- `docs/adr/004-frontend-architecture.md` — ADR: React + Zustand + React Router (why not Redux)
- `docs/BACKLOG.md` — M4 items marked ✅ Done
- `docs/PROGRESS.md` — this entry

**Tests:**
- `backend/tests/test_seed.py` — import test, seed() callable with mock session, verifies counts and commit

**Makefile:**
- `seed` target: `docker compose exec api python scripts/seed.py`
- `lighthouse` target: instructions for running Lighthouse CI

### Build verification
- `npm run type-check` — passes (0 errors)
- `npm run build` — passes, 996ms, PWA precache 17 entries
- Bundle: vendor chunk 53 KB gzipped, all pages 1–3.5 KB gzipped each

### Key decisions

- **Zustand over Redux** — 1/5th the boilerplate for 2 stores; see ADR 004
- **Lazy loading all pages** — `lazy()` + `<Suspense>` splits each page; vendor chunk separate
- **No public reaction counters** — consistent with M3 design; ReactionBar shows `aria-pressed` state only
- **Reciprocity gate in frontend** — `has_moment_today` from feed API, gate rendered before feed
- **Session nudge is frontend-only** — no backend event; `setTimeout(10min)` re-arms on dismiss
- **Seed uses sync SQLAlchemy** — seed script doesn't need async; simpler and more debuggable

<!-- Add new entries above this line -->
