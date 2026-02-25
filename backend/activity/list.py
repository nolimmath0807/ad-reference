from conn import get_db


def list_activity_logs(
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    with get_db() as (conn, cur):
        conditions = []
        params = []

        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)

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
        cols = [desc[0] for desc in cur.description]
        items = []
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
                elif hasattr(v, "hex"):
                    d[k] = str(v)
            items.append(d)

    return {"items": items, "total": total}
