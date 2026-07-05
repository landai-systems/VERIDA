# Multi-stage backend Dockerfile
# Builder stage: install deps
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/
RUN pip install --upgrade pip && pip install --no-cache-dir build wheel

# Final stage
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create venv
RUN python -m venv /app/.venv

# Copy source and install
COPY backend/ ./backend/
RUN /app/.venv/bin/pip install --upgrade pip && \
    /app/.venv/bin/pip install ./backend/

# Create non-root user
RUN addgroup --system verida && adduser --system --ingroup verida verida
USER verida

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "verida.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
