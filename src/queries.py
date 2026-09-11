"""
Domain query functions for the Thoughts Dashboard.

All queries use parameterized statements per specs/security/sql_injection_prevention.spec.
Column/table names are internal constants — never from user input.
"""
import logging
from typing import Any, Dict, List

from .database import DatabaseConnection

logger = logging.getLogger(__name__)

# Whitelist of columns allowed for ORDER BY (REQ-4 / sql_injection_prevention.spec)
ALLOWED_SORT_COLUMNS = {
    "id",
    "author",
    "status",
    "thumbs_up",
    "thumbs_down",
    "net_rating",
    "similarity_score",
    "created_at",
}

ALLOWED_SORT_DIRECTIONS = {"ASC", "DESC"}


def get_all_thoughts(
    db: DatabaseConnection,
    sort_column: str = "id",
    sort_direction: str = "ASC",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch all thoughts from the database.

    Parameters validated against whitelists before being interpolated into the
    query string (column/table names cannot be parameterised with %s in psycopg2).
    The LIMIT value is passed as a bound parameter.
    """
    # Whitelist validation — these values are internal, never raw user input,
    # but we guard defensively.
    if sort_column not in ALLOWED_SORT_COLUMNS:
        logger.warning("Invalid sort column requested: %s — falling back to 'id'", sort_column)
        sort_column = "id"

    sort_direction = sort_direction.upper()
    if sort_direction not in ALLOWED_SORT_DIRECTIONS:
        logger.warning("Invalid sort direction: %s — falling back to ASC", sort_direction)
        sort_direction = "ASC"

    # Column/direction come from the whitelist above, not user input.
    # The LIMIT value is bound via parameterised query.
    query = (
        f"SELECT id, content, author, status, "
        f"thumbs_up, thumbs_down, "
        f"(thumbs_up - thumbs_down) AS net_rating, "
        f"similarity_score "
        f"FROM thoughts "
        f"ORDER BY {sort_column} {sort_direction} "
        f"LIMIT %s"
    )
    logger.debug("Fetching thoughts (sort=%s %s, limit=%d)", sort_column, sort_direction, limit)
    return db.execute_query(query, (limit,))
