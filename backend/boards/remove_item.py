import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def remove_board_item(board_id: str, item_id: str, user_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id FROM boards WHERE id = %s AND user_id = %s",
            (board_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "보드를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        cur.execute(
            "DELETE FROM board_items WHERE id = %s AND board_id = %s RETURNING id",
            (item_id, board_id),
        )
        deleted = cur.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "보드 항목을 찾을 수 없습니다.",
                    "details": None,
                }
            })

        # Update board cover_image_url (use first remaining item's ad thumbnail, or NULL)
        cur.execute(
            """
            UPDATE boards
            SET updated_at = NOW(),
                cover_image_url = (
                    SELECT a.thumbnail_url FROM ads a
                    JOIN board_items bi ON bi.ad_id = a.id
                    WHERE bi.board_id = %s
                    ORDER BY bi.added_at ASC LIMIT 1
                )
            WHERE id = %s
            """,
            (board_id, board_id),
        )

    return {"message": "보드에서 광고가 제거되었습니다."}


def main(board_id: str, item_id: str, user_id: str) -> dict:
    return remove_board_item(board_id, item_id, user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove an item from a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.board_id, args.item_id, args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"remove_item_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
