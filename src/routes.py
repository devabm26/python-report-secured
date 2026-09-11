"""
HTTP route handlers for the Thoughts Dashboard.

Input validation per specs/security/web_security.spec REQ-10/REQ-11.
No database logic in routes — delegates to query functions (database_layer.spec REQ-4).
"""
import datetime
import logging

from flask import Blueprint, current_app, jsonify, render_template, request

from .queries import ALLOWED_SORT_COLUMNS, get_all_thoughts

logger = logging.getLogger(__name__)

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index() -> str:
    """Render the thoughts dashboard table."""
    db = current_app.config["DB"]

    # --- Input validation (REQ-10, REQ-11) ---
    sort_column = request.args.get("sort", "id")
    if sort_column not in ALLOWED_SORT_COLUMNS:
        sort_column = "id"

    sort_direction = request.args.get("direction", "ASC").upper()
    if sort_direction not in {"ASC", "DESC"}:
        sort_direction = "ASC"

    try:
        limit = int(request.args.get("limit", 500))
        limit = max(1, min(limit, 1000))  # clamp
    except ValueError:
        limit = 500

    try:
        thoughts = get_all_thoughts(db, sort_column, sort_direction, limit)
    except Exception as exc:
        logger.error("Error fetching thoughts: %s", exc)
        return render_template(
            "error.html",
            message="Could not load thoughts from the database.",
        ), 500

    return render_template(
        "thoughts.html",
        thoughts=thoughts,
        sort_column=sort_column,
        sort_direction=sort_direction,
        limit=limit,
        total=len(thoughts),
    )


@bp.route("/health")
def health():
    """Health check endpoint for container orchestration."""
    db = current_app.config["DB"]
    db_ok = db.ping()
    status = "healthy" if db_ok else "unhealthy"
    http_code = 200 if db_ok else 503
    return (
        jsonify(
            {
                "status": status,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "checks": {"database": "ok" if db_ok else "failed"},
            }
        ),
        http_code,
    )
