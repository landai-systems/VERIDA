# Multi-stage backend Dockerfile
# Build context: ./backend (set in docker-compose.yml)

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed for dependency install first (layer cache)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --no-cache-dir build wheel

# ── Final stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create venv
RUN python -m venv /app/.venv

# Copy source (context is already ./backend)
COPY . .

# Install the package into the venv
RUN /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install .

# Create non-root user
RUN addgroup --system verida && adduser --system --ingroup verida verida
USER verida

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "verida.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
