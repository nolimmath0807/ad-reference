import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from ads.model import Ad
from boards.model import BoardItem
from conn import get_db


def add_board_item(board_id: str, ad_id: str, user_id: str) -> dict:
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

        cur.execute("SELECT id FROM ads WHERE id = %s", (ad_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "광고를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        cur.execute(
            "SELECT id FROM board_items WHERE board_id = %s AND ad_id = %s",
            (board_id, ad_id),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "이미 보드에 추가된 광고입니다.",
                    "details": None,
                }
            })

        cur.execute(
            """
            INSERT INTO board_items (board_id, ad_id)
            VALUES (%s, %s)
            RETURNING id, board_id, ad_id, added_at
            """,
            (board_id, ad_id),
        )
        item_row = cur.fetchone()

        # Update board cover_image_url with first ad's thumbnail and updated_at
        cur.execute(
            """
            UPDATE boards
            SET updated_at = NOW(),
                cover_image_url = COALESCE(
                    cover_image_url,
                    (SELECT a.thumbnail_url FROM ads a
                     JOIN board_items bi ON bi.ad_id = a.id
                     WHERE bi.board_id = %s
                     ORDER BY bi.added_at ASC LIMIT 1)
                )
            WHERE id = %s
            """,
            (board_id, board_id),
        )

        cur.execute(
            """
            SELECT id, platform, format, advertiser_name,
                   advertiser_handle, advertiser_avatar_url,
                   thumbnail_url, preview_url, media_type,
                   ad_copy, cta_text, likes, comments, shares,
                   start_date, end_date, tags, landing_page_url,
                   created_at, saved_at
            FROM ads WHERE id = %s
            """,
            (ad_id,),
        )
        ad_row = cur.fetchone()

    ad = Ad(
        id=str(ad_row[0]),
        platform=ad_row[1],
        format=ad_row[2],
        advertiser_name=ad_row[3],
        advertiser_handle=ad_row[4],
        advertiser_avatar_url=ad_row[5],
        thumbnail_url=ad_row[6],
        preview_url=ad_row[7],
        media_type=ad_row[8],
        ad_copy=ad_row[9],
        cta_text=ad_row[10],
        likes=ad_row[11],
        comments=ad_row[12],
        shares=ad_row[13],
        start_date=ad_row[14],
        end_date=ad_row[15],
        tags=ad_row[16] if ad_row[16] else [],
        landing_page_url=ad_row[17],
        created_at=ad_row[18],
        saved_at=ad_row[19],
    )

    board_item = BoardItem(
        id=str(item_row[0]),
        board_id=str(item_row[1]),
        ad_id=str(item_row[2]),
        ad=ad,
        added_at=item_row[3],
    )

    return board_item.model_dump(mode="json")


def main(board_id: str, ad_id: str, user_id: str) -> dict:
    return add_board_item(board_id, ad_id, user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add an ad to a board")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--ad-id", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.board_id, args.ad_id, args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"add_item_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
