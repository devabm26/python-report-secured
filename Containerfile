# ================================================================================
# Thoughts Dashboard — Containerfile
# Runtime: registry.access.redhat.com/hi/python:latest (Hummingbird hardened,
#          Python 3.14, non-root UID 65532, no package manager — distroless-style)
# Builder: registry.access.redhat.com/ubi9/python-39:latest (has dnf to compile
#          native extensions; discarded after build — never ships in final image)
# Spec: specs/deployment/dockerfile.spec
# ================================================================================

# ── Stage 1: Builder (UBI9 — has dnf, gcc, postgresql-devel) ─────────────────
# The builder is never shipped. It exists only to compile psycopg2 and install
# all Python packages into /opt/venv, which is then copied to the runtime stage.
FROM registry.access.redhat.com/ubi9/python-39:latest AS builder

USER root
RUN dnf install -y \
        gcc \
        postgresql-devel \
        python3-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime (Hardened Image — no package manager, UID 65532) ─────────
FROM registry.access.redhat.com/hi/python:latest

# Python runtime settings — no secrets (injected at runtime via Kubernetes Secrets)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Copy only the pre-built venv — compiler and build tools stay in the builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Hardened image runs as UID 65532; use that for file ownership
COPY --chown=65532:0 src/    /app/src/
COPY --chown=65532:0 config/ /app/config/

# Explicitly set the hardened image's non-root user
USER 65532

EXPOSE 8080

# Health check — uses Python stdlib only (no curl/wget in distroless image)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" \
        || exit 1

# Production WSGI server — flask dev server is forbidden in containers (spec REQ-7)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", \
     "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", \
     "src.app:app"]
