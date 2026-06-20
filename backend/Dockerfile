# =============================================================
# activia-trace backend — Multi-stage Dockerfile (Easypanel convention)
# Stage 1: builder  — install Python deps with uv
# Stage 2: runtime  — slim Python 3.13, no build toolchain
# =============================================================

# ---- builder stage ----
FROM python:3.13-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution and install
RUN pip install --no-cache-dir uv

# Copy only dependency manifests first (layer cache optimisation)
COPY pyproject.toml ./

# Install all dependencies declared in pyproject.toml into a local .venv
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python .

# ---- runtime stage ----
FROM python:3.13-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy the pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY seed_dev.py ./

# Activate the venv by prepending it to PATH
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Easypanel convention: listen on PORT (default 8000)
EXPOSE 8000

USER appuser

# Health-check: verify the /health endpoint is reachable
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start uvicorn (Easypanel reads CMD)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
