import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def revoke_share_token(board_id: str, user_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, user_id FROM boards WHERE id = %s::uuid",
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
        cur.execute(
            "UPDATE boards SET share_token = NULL WHERE id = %s::uuid",
            (board_id,),
        )
        conn.commit()
    return {"success": True}


def main(board_id: str, user_id: str) -> dict:
    return revoke_share_token(board_id, user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Revoke share token for a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.board_id, args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"unshare_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
