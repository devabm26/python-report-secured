#!/usr/bin/env bash
# run_local.sh — Set up and run the Thoughts Dashboard locally.
#
# Usage:
#   ./run_local.sh          # default port 8080
#   PORT=9000 ./run_local.sh
#
# Requirements:
#   - Python 3.9+ on PATH
#   - .env file present in project root (already created; gitignored)
#   - Network access to the cluster DB (postgresql.thoughts-app.svc.cluster.local)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PORT="${PORT:-8080}"

# ── Colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Preflight checks ───────────────────────────────────────────────────────────
info "Thoughts Dashboard — local runner"
echo "  Project : ${SCRIPT_DIR}"
echo "  Port    : ${PORT}"
echo ""

if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.9 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: ${PYTHON_VERSION}"

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
    error ".env file not found at ${SCRIPT_DIR}/.env"
    error "Create it from config/.env.example and fill in DB_PASSWORD."
    exit 1
fi

# ── Virtual environment ────────────────────────────────────────────────────────
if [[ ! -d "${VENV_DIR}" ]]; then
    info "Creating virtual environment at ${VENV_DIR} ..."
    python3 -m venv "${VENV_DIR}"
fi

# Activate
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
info "Virtual environment activated"

# ── Dependencies ───────────────────────────────────────────────────────────────
info "Installing / verifying dependencies from requirements.txt ..."
pip install --quiet --upgrade pip
pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"
info "Dependencies installed"

# ── Confirm .env is gitignored (safety check) ─────────────────────────────────
if git -C "${SCRIPT_DIR}" check-ignore -q .env 2>/dev/null; then
    info ".env is gitignored — credentials are safe"
else
    warn ".env does not appear to be gitignored. Check .gitignore before committing."
fi

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
info "Starting Thoughts Dashboard on http://0.0.0.0:${PORT}"
info "Press Ctrl+C to stop."
echo ""

cd "${SCRIPT_DIR}"
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    "src.app:app"
