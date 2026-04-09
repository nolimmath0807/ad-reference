import argparse
import json
from datetime import datetime
from pathlib import Path

from ads.model import Ad
from conn import get_db


def list_featured(
    page: int = 1,
    limit: int = 20,
    platform: str | None = None,
    search: str | None = None,
) -> dict:
    offset = (page - 1) * limit

    conditions = []
    params = []
    if platform:
        conditions.append("a.platform = %s")
        params.append(platform)
    if search:
        conditions.append("a.advertiser_name ILIKE %s")
        params.append(f"%{search}%")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_db() as (conn, cur):
        cur.execute(
            f"SELECT COUNT(*) FROM featured_references fr JOIN ads a ON fr.ad_id = a.id {where_clause}",
            params,
        )
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT fr.id, fr.ad_id, fr.added_by, fr.added_at, fr.memo,
                   a.id, a.platform, a.format, a.advertiser_name, a.advertiser_handle,
                   a.advertiser_avatar_url, a.thumbnail_url, a.preview_url, a.media_type,
                   a.ad_copy, a.cta_text, a.likes, a.comments, a.shares,
                   a.start_date, a.end_date, a.tags, a.landing_page_url, a.created_at, a.saved_at
            FROM featured_references fr
            JOIN ads a ON fr.ad_id = a.id
            {where_clause}
            ORDER BY fr.added_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

    items = []
    for row in rows:
        ad = Ad(
            id=str(row[5]),
            platform=row[6],
            format=row[7],
            advertiser_name=row[8],
            advertiser_handle=row[9],
            advertiser_avatar_url=row[10],
            thumbnail_url=row[11],
            preview_url=row[12],
            media_type=row[13],
            ad_copy=row[14],
            cta_text=row[15],
            likes=row[16],
            comments=row[17],
            shares=row[18],
            start_date=row[19],
            end_date=row[20],
            tags=row[21] if row[21] else [],
            landing_page_url=row[22],
            created_at=row[23],
            saved_at=row[24],
        )
        items.append({
            "id": str(row[0]),
            "ad_id": str(row[1]),
            "added_by": str(row[2]) if row[2] else None,
            "added_at": row[3].isoformat(),
            "memo": row[4],
            "ad": ad.model_dump(mode="json"),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (offset + limit) < total,
    }


def main(page: int, limit: int, platform: str | None, search: str | None) -> dict:
    return list_featured(page=page, limit=limit, platform=platform, search=search)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List featured references")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--search", default=None)
    args = parser.parse_args()

    result = main(args.page, args.limit, args.platform, args.search)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
