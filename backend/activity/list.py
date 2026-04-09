from conn import get_db
from utils.serialize import rows_to_dicts


def list_activity_logs(
    event_type: str | None = None,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    with get_db() as (conn, cur):
        conditions = []
        params = []

        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cur.execute(f"SELECT COUNT(*) FROM activity_logs {where}", params)
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT id, event_type, event_subtype, title, message, metadata, created_at
            FROM activity_logs
            {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        items = rows_to_dicts(cur)

    return {"items": items, "total": total}
