.PHONY: up down check test lint migrate shell build-fe install seed lighthouse

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up --build -d

down:
	docker compose down

# ── Quality gate ──────────────────────────────────────────────────────────────
check: lint test

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	cd backend && python -m pytest tests/ -v --tb=short

# ── Linting / type-checking ───────────────────────────────────────────────────
lint:
	cd backend && python -m ruff check src/ tests/
	cd backend && python -m mypy src/verida/domain/ src/verida/application/
	cd backend && python -m bandit -r src/verida/ -ll
	cd frontend && npm run type-check
	cd frontend && npm run lint

# ── Database migrations ───────────────────────────────────────────────────────
migrate:
	docker compose exec -w /app api alembic -c /app/alembic.ini upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	docker compose exec -w /app api alembic -c /app/alembic.ini revision --autogenerate -m "$$msg"

# ── Interactive shell ─────────────────────────────────────────────────────────
shell:
	docker compose exec -w /app api python -c "import IPython; IPython.embed()"

# ── Frontend ──────────────────────────────────────────────────────────────────
build-fe:
	cd frontend && npm run build

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# ── Seed & Lighthouse ─────────────────────────────────────────────────────────
seed:
	docker compose exec -w /app api python scripts/seed.py

lighthouse:
	@echo "Lighthouse CI instructions:"
	@echo "  1. Open Chrome → DevTools → Lighthouse tab"
	@echo "  2. URL: http://localhost:5173"
	@echo "  3. Device: Mobile, Categories: Performance + Accessibility + PWA"
	@echo "  4. Target: ≥90 on all three"
	@echo ""
	@echo "CLI alternative (requires lighthouse npm package):"
	@echo "  npx lighthouse http://localhost:5173 --view --preset=perf --form-factor=mobile"
