# VERIDA — Proof-of-Human Social Web

> **Staging/demo only.** This app is never deployed to production — see [Security notes](#security-notes).

VERIDA is a privacy-first social web app where users share spontaneous daily moments captured live in-browser. The platform attests that content was created by a real human and has not been modified after capture — the antidote to AI-generated feeds.

---

## What you need to run VERIDA

Everything runs inside **Docker** — you do not need Python, Node.js, or PostgreSQL installed on your machine. The only two hard requirements are:

| Tool | Why | Minimum version |
|---|---|---|
| **Docker Desktop** | Runs the entire stack (API, DB, Redis, Mailpit, Frontend) | 24.x |
| **Git** | To clone the repo | any |
| **make** | Convenience wrapper around docker compose | any |
| **OpenSSL** (optional) | To generate a secure `SECRET_KEY` | any |

### 🪟 Windows

1. Install **Docker Desktop for Windows**: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Enable **WSL 2 backend** during setup (recommended) — or Hyper-V
   - After install, make sure Docker Desktop is running (whale icon in taskbar)
2. Install **Git for Windows**: [git-scm.com](https://git-scm.com/download/win)
3. `make` is included in **Git Bash** — use Git Bash as your terminal for all commands below
4. Generate a secret key in Git Bash: `openssl rand -hex 32`

> ⚠️ **Windows tip:** Run all commands in **Git Bash** (not PowerShell or CMD). Line endings and `make` work correctly there.

---

### 🐧 Linux (Ubuntu / Debian / Fedora / Arch)

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git make

# Add your user to the docker group (so you don't need sudo)
sudo usermod -aG docker $USER
newgrp docker

# Fedora
sudo dnf install -y docker docker-compose git make
sudo systemctl start docker && sudo systemctl enable docker

# Arch
sudo pacman -S docker docker-compose git make
sudo systemctl start docker && sudo systemctl enable docker
```

> ⚠️ **Linux tip:** If `make up` fails with a permission error, either run with `sudo` once or ensure your user is in the `docker` group (see above).

---

### 🍎 macOS

1. Install **Docker Desktop for Mac**: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Works on both Intel and Apple Silicon (M1/M2/M3)
2. `git` and `make` are pre-installed via Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```
3. Docker Desktop must be **running** (whale icon in menu bar) before using `make up`

> ⚠️ **Apple Silicon (M1/M2/M3) tip:** All images in docker-compose.yml support `linux/arm64`. No extra steps needed.

---

## Quick start (all platforms)

```bash
# 1. Clone the repo
git clone https://github.com/landai-systems/VERIDA.git
cd VERIDA

# 2. Create your local environment file
cp .env.example .env
```

Open `.env` and set at minimum:
```env
SECRET_KEY=<paste output of: openssl rand -hex 32>
```
All other values have working defaults for local development.

```bash
# 3. Start all services (first run downloads images — takes 2-3 min)
make up

# 4. Apply database migrations
make migrate

# 5. (Optional) Seed with demo data — 10 users, 30 posts, 3 circles
make seed
```

### ✅ Verify everything is running

| Service | URL | What it is |
|---|---|---|
| 🖥️ **Frontend** | http://localhost:5173 | React web app |
| 📖 **API Docs** | http://localhost:8000/docs | Swagger UI — try every endpoint |
| ❤️ **API Health** | http://localhost:8000/health | Should return `{"status": "ok"}` |
| 📧 **Mailpit** | http://localhost:8025 | Catches all outgoing emails (e-mail verification, etc.) |

---

## Demo walkthrough

```
Register → verify email (Mailpit) → capture your moment → unlock the feed
→ react to posts → manage circles → check your streak → export your data
```

Full step-by-step script: [docs/DEMO.md](docs/DEMO.md)

---

## Useful commands

| Command | What it does |
|---|---|
| `make up` | Start all services (builds images if needed) |
| `make down` | Stop all services |
| `make migrate` | Apply Alembic DB migrations |
| `make seed` | Load synthetic demo data (Faker, seed=42) |
| `make test` | Run the full pytest test suite (90+ tests) |
| `make check` | Full quality gate: lint + typecheck + tests |
| `make lint` | ruff + mypy + bandit |
| `make shell` | Python REPL inside the API container |
| `make logs` | Tail logs from all containers |

---

## Architecture

```
domain/          ← pure Python entities & value objects (zero external deps)
application/     ← use-cases, command/query handlers, port interfaces (Protocols)
infrastructure/  ← SQLAlchemy repos, Redis, email, authenticity heuristics, arq workers
api/             ← FastAPI routers, Pydantic schemas, middleware
```

**Dependency rule:** outer layers depend on inner layers — never the reverse.
**Tech stack:** Python 3.12 · FastAPI · PostgreSQL 16 · Redis · React + TypeScript + Vite · Tailwind · Docker Compose

---

## Security notes

- 🔒 **DO_NOT_DEPLOY guard** — the API refuses to start in `production` mode unless `PROD_RELEASE_APPROVED=explicit-human-signoff` is set manually by a human operator. Automation never sets this flag.
- 🔑 **Argon2id** password hashing (OWASP-recommended params)
- 🪙 **JWT** — 15-minute access tokens + rotating refresh tokens (httpOnly, Secure, SameSite=Strict cookies)
- 🚦 **Rate limiting** — Redis sliding-window on all auth and write endpoints
- 🛡️ **Security headers** — CSP (no unsafe-inline), HSTS, X-Frame-Options, Referrer-Policy
- 📋 **GDPR by design** — full data export (Art. 20) and hard delete (Art. 17) built in

---

## Documentation

| Document | Purpose |
|---|---|
| [DEMO.md](docs/DEMO.md) | Step-by-step demo script |
| [ROADMAP.md](docs/ROADMAP.md) | M1–M4 milestones |
| [TRUST_MODEL.md](docs/TRUST_MODEL.md) | What attestation proves (and doesn't) |
| [PRIVACY.md](docs/PRIVACY.md) | GDPR compliance (EN + DE) |
| [ENGAGEMENT.md](docs/ENGAGEMENT.md) | Ethical engagement mechanics |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | STRIDE threat model |
| [DATA_MAP.md](docs/DATA_MAP.md) | Personal data inventory |
| [ADR 001](docs/adr/001-clean-architecture.md) | Why Clean Architecture |
| [ADR 002](docs/adr/002-tech-stack.md) | Tech stack rationale |
| [ADR 003](docs/adr/003-consent-model.md) | Versioned consent model |
| [ADR 004](docs/adr/004-frontend-architecture.md) | Frontend architecture |

---

## Contributing

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat:` · `fix:` · `docs:` · `chore:` · `test:` · `refactor:` · `ci:`

```bash
make check   # must be green before opening a PR
```
