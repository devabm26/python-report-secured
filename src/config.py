"""
Configuration management for the Thoughts Dashboard.
Loads all settings from environment variables — no hardcoded values.
"""
import os
import logging

logger = logging.getLogger(__name__)


def get_required_env(key: str) -> str:
    """Return the value of a required environment variable or raise."""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable '{key}' is not set. "
                         f"Check your .env file or deployment secrets.")
    return value


class Config:
    """Application configuration loaded from environment variables."""

    # Flask
    SECRET_KEY: str = get_required_env("SECRET_KEY")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # Session cookies
    SESSION_COOKIE_SECURE: bool = not DEBUG
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PERMANENT_SESSION_LIFETIME: int = 3600

    # Database
    DB_HOST: str = get_required_env("DB_HOST")
    DB_NAME: str = get_required_env("DB_NAME")
    DB_USER: str = get_required_env("DB_USER")
    DB_PASSWORD: str = get_required_env("DB_PASSWORD")
    DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))
    DB_POOL_MIN: int = int(os.environ.get("DB_POOL_MIN", "1"))
    DB_POOL_MAX: int = int(os.environ.get("DB_POOL_MAX", "10"))

    def __init__(self) -> None:
        logger.info("Configuration loaded successfully (values redacted from logs)")
