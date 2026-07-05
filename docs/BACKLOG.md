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
| 11 | P0 | SQLAlchemy async models + Alembic migrations | ⬜ Open |
| 12 | P0 | Repository pattern implementations | ⬜ Open |
| 13 | P0 | Daily capture initiation endpoint | ⬜ Open |
| 14 | P0 | Media upload endpoint (presigned URL or direct) | ⬜ Open |
| 15 | P0 | Post submission + attestation trigger | ⬜ Open |
| 16 | P0 | Circle CRUD endpoints | ⬜ Open |
| 17 | P0 | Circle membership (invite, accept, remove) | ⬜ Open |
| 18 | P0 | Post feed (paginated, circle-filtered) | ⬜ Open |
| 19 | P0 | Email verification flow | ⬜ Open |
| 20 | P0 | arq background worker for attestation | ⬜ Open |
| 21 | P1 | Frontend: login / register pages | ⬜ Open |
| 22 | P1 | Frontend: capture flow (getUserMedia) | ⬜ Open |
| 23 | P1 | Frontend: feed page | ⬜ Open |
| 24 | P1 | Frontend: circle management | ⬜ Open |
| 25 | P1 | Frontend: profile page | ⬜ Open |

---

## M3 — Engagement (Sprint 4–5)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 26 | P1 | Reactions (emoji palette, limited) | ⬜ Open |
| 27 | P1 | Comments | ⬜ Open |
| 28 | P1 | Streak tracking + ethical guard rails | ⬜ Open |
| 29 | P1 | In-app notifications | ⬜ Open |
| 30 | P1 | Email digest notifications | ⬜ Open |
| 31 | P1 | Trust badges on posts | ⬜ Open |
| 32 | P1 | Report / moderation queue | ⬜ Open |
| 33 | P2 | Admin dashboard | ⬜ Open |
| 34 | P2 | Rate limiting (API gateway) | ⬜ Open |

---

## M4 — Scale & Hardening (Sprint 6+)

| # | Priority | Item | Status |
|---|----------|------|--------|
| 35 | P1 | Structured log shipping | ⬜ Open |
| 36 | P1 | Prometheus metrics + Grafana | ⬜ Open |
| 37 | P1 | GDPR data export (Article 20) | ⬜ Open |
| 38 | P1 | GDPR deletion (Article 17) | ⬜ Open |
| 39 | P2 | OpenTelemetry tracing | ⬜ Open |
| 40 | P2 | Pen test scope definition | ⬜ Open |
| 41 | P2 | Load test (100 RPS target) | ⬜ Open |
| 42 | P2 | Kubernetes manifests | ⬜ Open |

---

## Icebox (no milestone assigned)

- Federated identity (ActivityPub exploration)
- On-device ML liveness detection
- Audio moments (short clips)
- Branded mobile apps (iOS/Android via Capacitor)
