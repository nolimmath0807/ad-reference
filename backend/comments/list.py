import argparse
import json
from datetime import datetime
from pathlib import Path

from conn import get_db


def list_comments(ad_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT c.id, c.ad_id, c.user_id, c.content, c.created_at,
                   u.name AS user_name, u.avatar_url AS user_avatar_url
            FROM ad_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.ad_id = %s::uuid
            ORDER BY c.created_at ASC
            """,
            (ad_id,),
        )
        rows = cur.fetchall()

    items = [
        {
            "id": str(row[0]),
            "ad_id": str(row[1]),
            "user_id": str(row[2]),
            "content": row[3],
            "created_at": row[4].isoformat(),
            "user_name": row[5],
            "user_avatar_url": row[6],
        }
        for row in rows
    ]
    return {"items": items, "total": len(items)}


def main(ad_id: str) -> dict:
    return list_comments(ad_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List comments for an ad")
    parser.add_argument("--ad-id", required=True)
    args = parser.parse_args()

    result = main(args.ad_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
