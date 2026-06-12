# ── Multi-stage Dockerfile for activia-trace backend ─────────
# Builder stage: install dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml .

# Create minimal app/ so setuptools can resolve the editable install
RUN mkdir -p app && touch app/__init__.py

# Install build deps + project in a virtual env
RUN pip install --no-cache-dir -e ".[dev]"

# ── Runtime stage: slim image ────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Copy the pre-built venv from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ /app/app/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
