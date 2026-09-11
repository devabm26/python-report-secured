# ================================================================================
# Thoughts Dashboard — Containerfile
# Base image: Red Hat Hardened Images Python (enterprise-approved, non-root UID 1001)
# Spec: specs/deployment/dockerfile.spec
# ================================================================================

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM registry.access.redhat.com/hi/python:latest AS builder

# Install build-time dependencies (compiler + PostgreSQL headers for psycopg2)
USER root
RUN dnf install -y \
        gcc \
        postgresql-devel \
        python3-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Create an isolated virtual environment so only it gets copied to runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies — copy requirements first to leverage layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM registry.access.redhat.com/hi/python:latest

# Install only the runtime PostgreSQL client library (not the full devel stack)
USER root
RUN dnf install -y \
        libpq \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Python runtime settings — no secrets here (injected at runtime via env/Secrets)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application source — owned by UID 1001 (UBI default non-root user)
COPY --chown=1001:0 src/       /app/src/
COPY --chown=1001:0 config/    /app/config/

# UBI9 Python images run as UID 1001 by default; make it explicit
USER 1001

# Document the port the application listens on
EXPOSE 8080

# Health check — calls the /health endpoint defined in routes.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" \
        || exit 1

# Production WSGI server (gunicorn) — flask dev server is forbidden in containers
CMD ["sh", "-c", \
     "gunicorn --bind 0.0.0.0:${PORT} --workers 4 --timeout 60 \
      --access-logfile - --error-logfile - src.app:app"]
