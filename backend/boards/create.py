import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from boards.model import Board, BoardCreateRequest
from conn import get_db


def create_board(user_id: str, name: str, description: str = "") -> dict:
    request = BoardCreateRequest(name=name, description=description)

    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO boards (user_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id, name, description, cover_image_url, created_at, updated_at
            """,
            (user_id, request.name, request.description or ""),
        )
        row = cur.fetchone()

    board = Board(
        id=str(row[0]),
        name=row[1],
        description=row[2],
        cover_image_url=row[3],
        item_count=0,
        created_at=row[4],
        updated_at=row[5],
    )

    return board.model_dump(mode="json")


def main(user_id: str, name: str, description: str = "") -> dict:
    return create_board(user_id, name, description)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new board")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    result = main(args.user_id, args.name, args.description)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"create_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
