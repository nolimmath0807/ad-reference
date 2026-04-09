import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from ads.model import Ad
from boards.model import BoardItem
from conn import get_db


def get_shared_board(token: str, page: int = 1, limit: int = 20) -> dict:
    offset = (page - 1) * limit

    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT b.id, b.name, b.description, b.cover_image_url, b.created_at, b.updated_at,
                   u.name AS owner_name
            FROM boards b
            JOIN users u ON b.user_id = u.id
            WHERE b.share_token = %s
            """,
            (token,),
        )
        board_row = cur.fetchone()

        if not board_row:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "SHARED_BOARD_NOT_FOUND",
                        "message": "유효하지 않은 공유 링크입니다.",
                        "details": None,
                    }
                },
            )

        board_id = str(board_row[0])

        cur.execute(
            "SELECT COUNT(*) FROM board_items WHERE board_id = %s",
            (board_id,),
        )
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                bi.id AS bi_id, bi.board_id, bi.ad_id, bi.added_at,
                a.id AS ad_id_pk, a.platform, a.format, a.advertiser_name,
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
        item_cols = [desc[0] for desc in cur.description]
        item_rows = cur.fetchall()

    items = []
    for row in item_rows:
        d = dict(zip(item_cols, row))
        ad = Ad(
            id=str(d["ad_id_pk"]),
            platform=d["platform"],
            format=d["format"],
            advertiser_name=d["advertiser_name"],
            advertiser_handle=d["advertiser_handle"],
            advertiser_avatar_url=d["advertiser_avatar_url"],
            thumbnail_url=d["thumbnail_url"],
            preview_url=d["preview_url"],
            media_type=d["media_type"],
            ad_copy=d["ad_copy"],
            cta_text=d["cta_text"],
            likes=d["likes"],
            comments=d["comments"],
            shares=d["shares"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            tags=d["tags"] if d["tags"] else [],
            landing_page_url=d["landing_page_url"],
            created_at=d["created_at"],
            saved_at=d["saved_at"],
        )
        item = BoardItem(
            id=str(d["bi_id"]),
            board_id=str(d["board_id"]),
            ad_id=str(d["ad_id"]),
            ad=ad,
            added_at=d["added_at"],
        )
        items.append(item)

    return {
        "id": board_id,
        "name": board_row[1],
        "description": board_row[2],
        "cover_image_url": board_row[3],
        "created_at": board_row[4].isoformat() if board_row[4] else None,
        "updated_at": board_row[5].isoformat() if board_row[5] else None,
        "owner_name": board_row[6],
        "item_count": total,
        "items": [item.model_dump(mode="json") for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total,
    }


def main(token: str, page: int = 1, limit: int = 20) -> dict:
    return get_shared_board(token, page, limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get shared board detail by token")
    parser.add_argument("--token", required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    result = main(args.token, args.page, args.limit)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"shared_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
