import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def delete_board(board_id: str, user_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id FROM boards WHERE id = %s AND user_id = %s",
            (board_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "BOARD_NOT_FOUND",
                    "message": "Board not found",
                    "details": None,
                }
            })

        cur.execute(
            "DELETE FROM board_items WHERE board_id = %s",
            (board_id,),
        )

        cur.execute(
            "DELETE FROM boards WHERE id = %s AND user_id = %s RETURNING id",
            (board_id, user_id),
        )
        deleted = cur.fetchone()

    return {"id": str(deleted[0]), "deleted": True}


def main(board_id: str, user_id: str) -> dict:
    return delete_board(board_id, user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.board_id, args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"delete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
