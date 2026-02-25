import json
import logging

from conn import get_db

logger = logging.getLogger("activity_log")


def log_activity(
    event_type: str,
    title: str,
    message: str = "",
    event_subtype: str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        with get_db() as (conn, cur):
            cur.execute(
                """
                INSERT INTO activity_logs (event_type, event_subtype, title, message, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_type,
                    event_subtype,
                    title,
                    message,
                    json.dumps(metadata or {}, ensure_ascii=False, default=str),
                ),
            )
    except Exception as e:
        logger.warning(f"Failed to write activity log: {e}")
