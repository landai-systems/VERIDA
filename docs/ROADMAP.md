# VERIDA Roadmap

## Overview

VERIDA is built in four milestones, each shippable.
Every milestone adds user-facing value; no milestone exists solely to build infrastructure.

---

## M1 — Foundation (current)

**Goal:** Repo structure, CI pipeline, auth scaffold, security controls.

**Deliverables:**
- Clean Architecture scaffold (domain → application → infrastructure → api)
- User registration and login with Argon2id + JWT
- Rotating refresh tokens
- DO_NOT_DEPLOY guard (blocks accidental production deployment)
- Docker Compose dev environment (API, DB, Redis, Mailpit, Frontend)
- GitHub Actions CI (lint, type-check, tests, bandit, pip-audit, gitleaks)
- PWA shell with routing
- Documentation foundation (Trust Model, Privacy, Threat Model, ADRs)

**Exit criteria:**
- `make check` passes from a clean clone
- `make up` boots all services successfully
- Auth endpoints return correct status codes

---

## M2 — Core Social Features

**Goal:** Users can post daily moments; circles define visibility.

**Deliverables:**
- Daily capture flow: initiate → capture in-browser → submit with hash
- SQLAlchemy 2.0 async repositories (replaces M1 in-memory stores)
- Alembic migrations (users, posts, circles, refresh_tokens)
- Attestation pipeline: HeuristicAuthenticityChecker integrated
- Circles: create, invite, accept/reject, remove members
- Post feed: paginated, filtered by circles
- Email verification via Mailpit (dev) / SMTP (staging)
- Frontend: login, register, capture, feed, circle management pages
- Background worker (arq): attestation runs async

**Exit criteria:**
- User can register, capture a moment, post to a circle, see feed
- Attestation status visible on post

---

## M3 — Engagement & Trust

**Goal:** Deepen engagement while being honest about what attestation proves.

**Deliverables:**
- Reactions (not "likes" — curated emotion palette)
- Comments with attestation context
- Streaks: consecutive daily moments, with ethical design guard rails
- Notification system (in-app + email digest)
- Trust badges: visible attestation status, honest caveats
- Report / moderation queue
- Admin dashboard (internal only)
- Rate limiting at API gateway layer

**Exit criteria:**
- Streak system implemented with mandatory cooldown periods
- Moderation queue functional
- Notification emails delivered in staging

---

## M4 — Scale & Hardening

**Goal:** Production-ready deployment with observability and compliance.

**Deliverables:**
- Structured logging (structlog JSON) shipped to log aggregator
- Prometheus metrics + Grafana dashboard
- OpenTelemetry trace propagation
- GDPR data export (Article 20 portability) and deletion (Article 17)
- Penetration test scope definition
- Full STRIDE mitigations documented
- Caddy / Traefik TLS termination config
- Kubernetes manifests (optional — only if team size warrants it)
- Privacy impact assessment (PIA) updated

**Exit criteria:**
- All GDPR rights automated and tested
- P99 API latency < 200 ms under 100 RPS load test
- Zero HIGH/CRITICAL findings in SAST + dependency scan
