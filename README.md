# VERIDA — Proof-of-Human Social Web

> **Staging only.** `PROD_RELEASE_APPROVED` is never set by automation.

VERIDA is a privacy-first social web application where users share spontaneous daily moments captured live in-browser. The platform attests that content is created by a real human and has not been modified after capture.

---

## 5-Minute Onboarding

### Prerequisites

| Tool | Version |
|------|---------|
| Docker + Compose | ≥ 24 |
| Python | 3.12 |
| Node.js | ≥ 20 |
| make | any |

### Quick start

```bash
# 1. Clone
git clone https://github.com/landai-systems/VERIDA.git
cd VERIDA

# 2. Configure environment
cp .env.example .env
# Edit .env — set at minimum: SECRET_KEY, DATABASE_URL, REDIS_URL

# 3. Boot all services
make up

# 4. Run checks
make check
```

The API is available at `http://localhost:8000`.  
The frontend dev server is at `http://localhost:5173`.  
Mailpit (local SMTP catcher) is at `http://localhost:8025`.

### Key make targets

| Target | What it does |
|--------|-------------|
| `make up` | Start all Docker Compose services |
| `make down` | Stop all services |
| `make check` | Full quality gate: lint + typecheck + test |
| `make test` | Run pytest suite |
| `make lint` | ruff + mypy + bandit |
| `make migrate` | Apply Alembic migrations |
| `make shell` | Python REPL inside the API container |

---

## Architecture

```
domain/          ← pure Python entities & value objects (no external deps)
application/     ← use-cases, command/query handlers, port interfaces
infrastructure/  ← DB adapters, cache, email, authenticity heuristics
api/             ← FastAPI routers, schemas, middleware
```

Dependency rule: outer layers depend on inner layers, never the reverse.
Interfaces (Protocols) live in `application/ports.py`.

---

## Security notes

- **DO_NOT_DEPLOY guard**: the API refuses to start in `production` mode unless `PROD_RELEASE_APPROVED=explicit-human-signoff` is set by a human operator.
- Passwords hashed with Argon2id.
- JWTs: 15-minute access tokens + rotating refresh tokens stored as httpOnly cookies.
- All secrets loaded from environment variables; validated at startup.

---

## Docs

| Document | Purpose |
|----------|---------|
| [ROADMAP](docs/ROADMAP.md) | M1–M4 milestones |
| [BACKLOG](docs/BACKLOG.md) | Prioritized task list |
| [TRUST_MODEL](docs/TRUST_MODEL.md) | What attestation proves (and doesn't) |
| [PRIVACY](docs/PRIVACY.md) | GDPR compliance |
| [THREAT_MODEL](docs/THREAT_MODEL.md) | STRIDE analysis |
| [ADR 001](docs/adr/001-clean-architecture.md) | Clean Architecture decision |
| [ADR 002](docs/adr/002-tech-stack.md) | Tech stack rationale |

---

## Contributing

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `ci:`

```bash
make lint   # must pass before opening a PR
make test   # must be green
```
