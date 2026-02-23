import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from ads.model import Ad
from boards.model import BoardDetailResponse, BoardItem
from conn import get_db


def get_board_detail(board_id: str, user_id: str, page: int = 1, limit: int = 20) -> dict:
    offset = (page - 1) * limit

    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, name, description, cover_image_url, created_at, updated_at
            FROM boards
            WHERE id = %s AND user_id = %s
            """,
            (board_id, user_id),
        )
        board_row = cur.fetchone()

        if not board_row:
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "보드를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        cur.execute(
            "SELECT COUNT(*) FROM board_items WHERE board_id = %s",
            (board_id,),
        )
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                bi.id, bi.board_id, bi.ad_id, bi.added_at,
                a.id, a.platform, a.format, a.advertiser_name,
                a.advertiser_handle, a.advertiser_avatar_url,
                a.thumbnail_url, a.preview_url, a.media_type,
                a.ad_copy, a.cta_text, a.likes, a.comments, a.shares,
                a.start_date, a.end_date, a.tags, a.landing_page_url,
                a.created_at, a.saved_at
            FROM board_items bi
            JOIN ads a ON a.id = bi.ad_id
            WHERE bi.board_id = %s
            ORDER BY bi.added_at DESC
            LIMIT %s OFFSET %s
            """,
            (board_id, limit, offset),
        )
        item_rows = cur.fetchall()

    items = []
    for row in item_rows:
        ad = Ad(
            id=str(row[4]),
            platform=row[5],
            format=row[6],
            advertiser_name=row[7],
            advertiser_handle=row[8],
            advertiser_avatar_url=row[9],
            thumbnail_url=row[10],
            preview_url=row[11],
            media_type=row[12],
            ad_copy=row[13],
            cta_text=row[14],
            likes=row[15],
            comments=row[16],
            shares=row[17],
            start_date=row[18],
            end_date=row[19],
            tags=row[20] if row[20] else [],
            landing_page_url=row[21],
            created_at=row[22],
            saved_at=row[23],
        )
        item = BoardItem(
            id=str(row[0]),
            board_id=str(row[1]),
            ad_id=str(row[2]),
            ad=ad,
            added_at=row[3],
        )
        items.append(item)

    response = BoardDetailResponse(
        id=str(board_row[0]),
        name=board_row[1],
        description=board_row[2],
        cover_image_url=board_row[3],
        item_count=total,
        created_at=board_row[4],
        updated_at=board_row[5],
        items=items,
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total,
    )

    return response.model_dump(mode="json")


def main(board_id: str, user_id: str, page: int = 1, limit: int = 20) -> dict:
    return get_board_detail(board_id, user_id, page, limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get board detail with items")
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    result = main(args.board_id, args.user_id, args.page, args.limit)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
