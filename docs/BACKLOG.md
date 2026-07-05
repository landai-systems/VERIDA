# VERIDA Backlog

Priority: P0 (must, M1) → P1 (should, M2) → P2 (nice-to-have, M3+)

---

## M1 — Foundation (Sprint 1)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 1 | P0 | Repo scaffold — all M1 files | ✅ Done |
| 2 | P0 | DO_NOT_DEPLOY guard + test | ✅ Done |
| 3 | P0 | Auth endpoints (register, login, refresh, logout) | ✅ Done |
| 4 | P0 | GitHub Actions CI pipeline | ✅ Done |
| 5 | P0 | Docker Compose dev environment | ✅ Done |
| 6 | P0 | Trust Model documentation | ✅ Done |
| 7 | P0 | Privacy / GDPR documentation | ✅ Done |
| 8 | P0 | STRIDE threat model skeleton | ✅ Done |
| 9 | P0 | ADR 001: Clean Architecture | ✅ Done |
| 10 | P0 | ADR 002: Tech Stack | ✅ Done |

---

## M2 — Core Social (Sprint 2–3)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 11 | P0 | SQLAlchemy async models + Alembic migrations | ✅ Done |
| 12 | P0 | Repository pattern implementations | ✅ Done |
| 13 | P0 | Daily capture initiation endpoint | ✅ Done |
| 14 | P0 | Media upload endpoint (presigned URL or direct) | ✅ Done |
| 15 | P0 | Post submission + attestation trigger | ✅ Done |
| 16 | P0 | Circle CRUD endpoints | ✅ Done |
| 17 | P0 | Circle membership (invite, accept, remove) | ✅ Done |
| 18 | P0 | Post feed (paginated, circle-filtered, reciprocity-gated) | ✅ Done |
| 19 | P0 | Email verification flow | ✅ Done |
| 20 | P0 | arq background worker for attestation | ✅ Done |
| 21 | P1 | Frontend: login / register pages | ⬜ Open |
| 22 | P1 | Frontend: capture flow (getUserMedia) | ⬜ Open |
| 23 | P1 | Frontend: feed page | ⬜ Open |
| 24 | P1 | Frontend: circle management | ⬜ Open |
| 25 | P1 | Frontend: profile page | ⬜ Open |

---

## M3 — Trust & Compliance (Sprint 4–5)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 26 | P1 | Reactions (warm emoji palette, no public counters) | ✅ Done |
| 27 | P1 | Comments (plain-text, max 500 chars) | ✅ Done |
| 28 | P1 | Streak tracking + grace days (max 2/month, no guilt copy) | ✅ Done |
| 29 | P1 | Trust badges on posts (based on attestation status) | ✅ Done |
| 30 | P1 | Authenticity port upgrade (Redis phash, EXIF, timing, gallery) | ✅ Done |
| 31 | P1 | AttestationUseCase orchestrator | ✅ Done |
| 32 | P1 | Consent management (versioned, granular, Art. 7 compliant) | ✅ Done |
| 33 | P1 | GDPR data export (Article 20) | ✅ Done |
| 34 | P1 | GDPR erasure (Article 17, hard delete + purge job) | ✅ Done |
| 35 | P1 | Rate limiting (Redis sliding window, auth + write endpoints) | ✅ Done |
| 36 | P1 | Security headers (HSTS, CSP no-unsafe-inline, X-Frame, etc.) | ✅ Done |
| 37 | P1 | Alembic migration 0002 (consent, reactions, comments, streaks) | ✅ Done |
| 38 | P1 | Privacy docs complete (Art. 17/20, consent flows, German summary) | ✅ Done |
| 39 | P1 | DATA_MAP updated with M3 entities | ✅ Done |
| 40 | P1 | THREAT_MODEL updated with M3 attack surfaces | ✅ Done |
| 41 | P1 | ENGAGEMENT.md (streak mechanics + ethical rationale) | ✅ Done |
| 42 | P1 | TRUST_MODEL.md updated (upgraded heuristics, honest limits) | ✅ Done |
| 43 | P1 | ADR 003: Consent model | ✅ Done |
| 44 | P1 | Test suite: consent, GDPR, reactions, comments, streaks | ✅ Done |
| 45 | P2 | In-app notifications | ⬜ Open |
| 46 | P2 | Email digest notifications | ⬜ Open |
| 47 | P2 | Report / moderation queue | ⬜ Open |
| 48 | P2 | Admin dashboard | ⬜ Open |

---

## M4 — Polish & Demo (Sprint 6)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 49 | P1 | Complete frontend UI (React + TS + Vite + Tailwind, PWA) | ✅ Done |
| 50 | P1 | Pages: Login, Register, Feed, Capture, Circles, Profile, Archive, Settings | ✅ Done |
| 51 | P1 | Components: Layout, PostCard, CameraCapture, ReactionBar, CommentSection, StreakBadge, AttestationBadge, EmptyState, ErrorBoundary, SessionNudge | ✅ Done |
| 52 | P1 | API client (axios, JWT auto-attach, auto-refresh on 401) | ✅ Done |
| 53 | P1 | Zustand stores: authStore, feedStore | ✅ Done |
| 54 | P1 | PWA manifest + Workbox service worker | ✅ Done |
| 55 | P1 | Reciprocity gate UI | ✅ Done |
| 56 | P1 | Session-end nudge (10 min) | ✅ Done |
| 57 | P1 | "You're all caught up" end-of-feed marker | ✅ Done |
| 58 | P1 | Archive view ("Your Authentic Year") | ✅ Done |
| 59 | P1 | Seed script (Faker seed=42, 10 users, 30 posts, 3 circles) | ✅ Done |
| 60 | P1 | Backend Dockerfile (multi-stage) | ✅ Done |
| 61 | P1 | Frontend Dockerfile.dev | ✅ Done |
| 62 | P1 | docs/DEMO.md — demo script | ✅ Done |
| 63 | P1 | ADR 004: Frontend architecture | ✅ Done |
| 64 | P1 | Makefile: seed + lighthouse targets | ✅ Done |
| 65 | P1 | backend/tests/test_seed.py | ✅ Done |

## Remaining (Post-M4, Icebox)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 66 | P2 | Structured log shipping | ⬜ Open |
| 67 | P2 | Prometheus metrics + Grafana | ⬜ Open |
| 68 | P2 | OpenTelemetry tracing | ⬜ Open |
| 69 | P2 | Pen test scope definition | ⬜ Open |
| 70 | P2 | Load test (100 RPS target) | ⬜ Open |
| 71 | P2 | Kubernetes manifests | ⬜ Open |

---

## Icebox (no milestone assigned)

- Federated identity (ActivityPub exploration)
- On-device ML liveness detection
- Audio moments (short clips)
- Branded mobile apps (iOS/Android via Capacitor)
