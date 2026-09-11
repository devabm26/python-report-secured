"""
Application entry point — Thoughts Dashboard.

Startup sequence per specs/architecture/web_application.spec:
1. Load env vars
2. Configure logging
3. Validate config (fail-fast)
4. Initialise Flask + security
5. Initialise database pool
6. Register routes
7. Register error handlers
"""
import logging
import os

from dotenv import load_dotenv

# Load .env before anything reads env vars
load_dotenv()

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

from .config import Config
from .database import DatabaseConnection
from .routes import bp as dashboard_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory."""
    config = Config()

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # --- Flask core config ---
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG
    app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
    app.config["PERMANENT_SESSION_LIFETIME"] = config.PERMANENT_SESSION_LIFETIME

    # --- CSRF protection (REQ-7) ---
    csrf = CSRFProtect(app)
    # Health endpoint is read-only — exempt from CSRF (REQ-9)
    csrf.exempt(dashboard_bp)  # GET-only blueprint; no state-changing POSTs

    # --- Security headers on every response (REQ-1) ---
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        )
        if not app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # --- Database pool ---
    db = DatabaseConnection(config)
    app.config["DB"] = db

    @app.teardown_appcontext
    def close_db(_exc):
        pass  # Pool managed at app level; closed on shutdown below

    # --- Routes ---
    app.register_blueprint(dashboard_bp)

    # --- Error handlers (REQ-17, REQ-18) ---
    @app.errorhandler(404)
    def not_found(_err):
        return render_template("error.html", message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(err):
        logger.error("Internal server error: %s", err)
        return render_template("error.html", message="An internal error occurred"), 500

    logger.info("Application initialised successfully")
    return app


# Gunicorn / direct run entry point
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
