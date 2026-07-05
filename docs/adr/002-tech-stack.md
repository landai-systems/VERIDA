# ADR 002 — Tech Stack

**Date:** 2026-07-05  
**Status:** Accepted  
**Deciders:** landai-systems engineering

---

## Context

We need a tech stack for VERIDA that:
1. Enables a small team to move fast
2. Is mature enough for production use
3. Supports async-first I/O (media uploads, background attestation)
4. Has strong typing support for maintainability
5. Is open source with permissive or compatible licencing

---

## Decision

### Backend

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.12 | Team expertise; excellent async support; rich ecosystem |
| Web framework | FastAPI | Native async; OpenAPI docs; Pydantic v2 integration; fast |
| Validation | Pydantic v2 | Performance (Rust core); strict mode; settings management |
| ORM | SQLAlchemy 2.0 (async) | Mature; async support; repository pattern compatible |
| Migrations | Alembic | Standard SQLAlchemy companion; auto-generate from models |
| Password hashing | Argon2id (argon2-cffi) | OWASP recommended; winner of Password Hashing Competition |
| JWT | python-jose | JWT + JWE; widely used |
| Background jobs | arq | Async-native Redis queue; simple API |
| Logging | structlog | Structured JSON output; OTel-ready |
| HTTP client | httpx | Async-native; used in tests |

### Database / Cache

| Component | Choice | Reason |
|-----------|--------|--------|
| Primary DB | PostgreSQL 16 | ACID; JSONB for metadata; uuid extension; proven at scale |
| Cache / Queue | Redis 7 | arq jobs; session cache; rate limiting tokens |

### Frontend

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | TypeScript | Type safety; better IDE support than plain JS |
| Framework | React 18 | Team expertise; large ecosystem; concurrent features |
| Build | Vite | Fast HMR; excellent TypeScript support; PWA plugin |
| Styling | Tailwind CSS | Utility-first; no heavy UI kit to avoid bundle bloat |
| PWA | vite-plugin-pwa (Workbox) | Service worker; offline support; install prompt |
| Routing | React Router v6 | Standard; file-based routing planned for M2 |

### Infrastructure

| Component | Choice | Reason |
|-----------|--------|--------|
| Containerisation | Docker + Docker Compose | Standard; reproducible dev environment |
| Reverse proxy | Caddy (staging) | Automatic HTTPS; simple config |
| CI | GitHub Actions | Already on GitHub; large action marketplace |
| Dev email | Mailpit | Local SMTP catcher; no external service needed |

### Observability

| Component | Choice | Reason |
|-----------|--------|--------|
| Logging | structlog (JSON) | Machine-parseable; correlatable with request IDs |
| Metrics | Prometheus (M4) | Standard; compatible with Grafana |
| Tracing | OpenTelemetry (M4) | Vendor-neutral; structlog is OTel-ready |

---

## Consequences

### Positive

- Single language (Python) for all backend reduces cognitive overhead.
- Async everywhere eliminates the sync/async impedance mismatch.
- Pydantic v2 gives runtime validation with Rust-level performance.
- PostgreSQL JSONB allows schema-less metadata without abandoning ACID.

### Negative

- Python GIL limits CPU-bound concurrency (mitigated by async I/O + arq workers).
- FastAPI is younger than Django; fewer built-in batteries.
- Tailwind generates large CSS in development (mitigated by PurgeCSS in build).

### Neutral

- No heavy UI kit is a conscious choice: we write our own components.
  This takes more time upfront but avoids vendor lock-in and bundle bloat.

---

## Alternatives considered

| Component | Alternative | Reason rejected |
|-----------|-------------|----------------|
| Web framework | Django | Sync-first; heavy ORM coupling |
| Web framework | Litestar | Smaller community; less documentation |
| ORM | Tortoise ORM | Less mature; fewer contributors |
| Background jobs | Celery | Complex config; sync-first heritage |
| Frontend | Next.js | SSR not needed for M1; adds complexity |
| Frontend | Vue 3 | React is team preference |
| Styling | shadcn/ui | Heavy dependency; want minimal bundle |

---

## Review trigger

This ADR should be revisited if:
- Team size exceeds 10 engineers (may warrant stronger typing, different patterns)
- Python performance becomes a bottleneck (may warrant Go microservices for hot paths)
- Mobile-first strategy requires native apps (may add Capacitor or React Native)
