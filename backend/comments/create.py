import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def create_comment(ad_id: str, user_id: str, content: str) -> dict:
    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "EMPTY_CONTENT", "message": "댓글 내용을 입력해주세요.", "details": None}},
        )

    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO ad_comments (ad_id, user_id, content)
            VALUES (%s::uuid, %s::uuid, %s)
            RETURNING id, ad_id, user_id, content, created_at
            """,
            (ad_id, user_id, content),
        )
        row = cur.fetchone()

        cur.execute("SELECT name, avatar_url FROM users WHERE id = %s::uuid", (user_id,))
        user_row = cur.fetchone()
        conn.commit()

    return {
        "id": str(row[0]),
        "ad_id": str(row[1]),
        "user_id": str(row[2]),
        "content": row[3],
        "created_at": row[4].isoformat(),
        "user_name": user_row[0] if user_row else "",
        "user_avatar_url": user_row[1] if user_row else None,
    }


def main(ad_id: str, user_id: str, content: str) -> dict:
    return create_comment(ad_id, user_id, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a comment")
    parser.add_argument("--ad-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()

    result = main(args.ad_id, args.user_id, args.content)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"create_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
