# VERIDA Progress Log

This file tracks milestone completions and significant decisions.
Newest entries first.

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
