import argparse
import json
from datetime import datetime
from pathlib import Path

from boards.model import Board, BoardListResponse
from conn import get_db


def list_boards(user_id: str, page: int = 1, limit: int = 12) -> dict:
    offset = (page - 1) * limit

    with get_db() as (conn, cur):
        cur.execute(
            "SELECT COUNT(*) FROM boards WHERE user_id = %s",
            (user_id,),
        )
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                b.id, b.name, b.description, b.cover_image_url,
                b.created_at, b.updated_at,
                (SELECT COUNT(*) FROM board_items bi WHERE bi.board_id = b.id) AS item_count
            FROM boards b
            WHERE b.user_id = %s
            ORDER BY b.updated_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()

    boards = [
        Board(
            id=str(row[0]),
            name=row[1],
            description=row[2],
            cover_image_url=row[3],
            item_count=row[6],
            created_at=row[4],
            updated_at=row[5],
        )
        for row in rows
    ]

    response = BoardListResponse(
        items=boards,
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total,
    )

    return response.model_dump(mode="json")


def main(user_id: str, page: int = 1, limit: int = 12) -> dict:
    return list_boards(user_id, page, limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List boards for a user")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    result = main(args.user_id, args.page, args.limit)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
