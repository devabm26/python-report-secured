"""
Database connection layer for the Thoughts Dashboard.

Architecture per specs/architecture/database_layer.spec:
- Connection pooling via psycopg2.pool.SimpleConnectionPool
- Context managers for safe connection lifecycle
- All queries 100% parameterized (specs/security/sql_injection_prevention.spec)
- Credentials from environment only (specs/security/secrets_management.spec)
"""
import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from .config import Config

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages a connection pool and provides safe query execution methods."""

    def __init__(self, config: Config) -> None:
        logger.info(
            "Initializing database connection pool (host=%s, db=%s, pool=%d-%d)",
            config.DB_HOST,
            config.DB_NAME,
            config.DB_POOL_MIN,
            config.DB_POOL_MAX,
        )
        try:
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=config.DB_POOL_MIN,
                maxconn=config.DB_POOL_MAX,
                host=config.DB_HOST,
                port=config.DB_PORT,
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                connect_timeout=30,
            )
            logger.info("Database connection pool initialised successfully")
        except psycopg2.OperationalError as exc:
            logger.error("Failed to create database connection pool: %s", exc)
            raise

    @contextmanager
    def get_connection(self) -> Generator:
        """Yield a connection from the pool and return it when done."""
        conn = self._pool.getconn()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dicts.

        Parameters
        ----------
        query:  SQL string with %s placeholders — NO f-strings or concatenation.
        params: Tuple of values to bind; never include user input in query string.
        """
        logger.debug("Executing SELECT query (params omitted from log)")
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def ping(self) -> bool:
        """Return True if the database is reachable, False otherwise."""
        try:
            self.execute_query("SELECT 1")
            return True
        except Exception as exc:
            logger.error("Database ping failed: %s", exc)
            return False

    def close(self) -> None:
        """Close all connections in the pool."""
        self._pool.closeall()
        logger.info("Database connection pool closed")
