import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def generate_share_token(board_id: str, user_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, user_id, share_token FROM boards WHERE id = %s::uuid",
            (board_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "BOARD_NOT_FOUND",
                        "message": "보드를 찾을 수 없습니다.",
                        "details": None,
                    }
                },
            )
        if str(row[1]) != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "권한이 없습니다.",
                        "details": None,
                    }
                },
            )
        if row[2]:
            return {"share_token": row[2]}
        token = str(uuid.uuid4())
        cur.execute(
            "UPDATE boards SET share_token = %s WHERE id = %s::uuid",
            (token, board_id),
        )
        conn.commit()
    return {"share_token": token}


def main(board_id: str, user_id: str) -> dict:
    return generate_share_token(board_id, user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate share token for a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.board_id, args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"share_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
