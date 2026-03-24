import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from boards.model import Board, BoardUpdateRequest
from conn import get_db


def update_board(board_id: str, user_id: str, name: str = None, description: str = None) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, user_id FROM boards WHERE id = %s",
            (board_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "보드를 찾을 수 없습니다.",
                    "details": None,
                }
            })
        if str(row[1]) != user_id:
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "보드를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        updates = []
        params = []
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)

        if not updates:
            raise HTTPException(status_code=400, detail={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "수정할 내용이 없습니다.",
                    "details": None,
                }
            })

        updates.append("updated_at = now()")
        params.append(board_id)

        cur.execute(
            f"""
            UPDATE boards SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, description, cover_image_url, created_at, updated_at
            """,
            params,
        )
        updated = cur.fetchone()

        cur.execute(
            "SELECT COUNT(*) FROM board_items WHERE board_id = %s",
            (board_id,),
        )
        item_count = cur.fetchone()[0]

    board = Board(
        id=str(updated[0]),
        name=updated[1],
        description=updated[2],
        cover_image_url=updated[3],
        item_count=item_count,
        created_at=updated[4],
        updated_at=updated[5],
    )

    return board.model_dump(mode="json")


def main(board_id: str, user_id: str, name: str = None, description: str = None) -> dict:
    return update_board(board_id, user_id, name, description)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    result = main(args.board_id, args.user_id, args.name, args.description)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
