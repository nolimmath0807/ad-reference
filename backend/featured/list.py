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
        # COUNT는 ad 단위 (GROUP BY ad_id)
        cur.execute(
            f"SELECT COUNT(DISTINCT fr.ad_id) FROM featured_references fr JOIN ads a ON fr.ad_id = a.id {where_clause}",
            params,
        )
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT
                fr.ad_id,
                MIN(fr.added_at) AS first_added_at,
                json_agg(
                    json_build_object(
                        'id', u.id::text,
                        'name', u.name,
                        'avatar_url', u.avatar_url,
                        'added_at', fr.added_at
                    ) ORDER BY fr.added_at ASC
                ) AS curators,
                a.id, a.platform, a.format, a.advertiser_name, a.advertiser_handle,
                a.advertiser_avatar_url, a.thumbnail_url, a.preview_url, a.media_type,
                a.ad_copy, a.cta_text, a.likes, a.comments, a.shares,
                a.start_date, a.end_date, a.tags, a.landing_page_url, a.created_at, a.saved_at
            FROM featured_references fr
            JOIN ads a ON fr.ad_id = a.id
            LEFT JOIN users u ON fr.added_by = u.id
            {where_clause}
            GROUP BY fr.ad_id,
                     a.id, a.platform, a.format, a.advertiser_name, a.advertiser_handle,
                     a.advertiser_avatar_url, a.thumbnail_url, a.preview_url, a.media_type,
                     a.ad_copy, a.cta_text, a.likes, a.comments, a.shares,
                     a.start_date, a.end_date, a.tags, a.landing_page_url, a.created_at, a.saved_at
            ORDER BY first_added_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

    items = []
    for row in rows:
        ad = Ad(
            id=str(row[3]),
            platform=row[4],
            format=row[5],
            advertiser_name=row[6],
            advertiser_handle=row[7],
            advertiser_avatar_url=row[8],
            thumbnail_url=row[9],
            preview_url=row[10],
            media_type=row[11],
            ad_copy=row[12],
            cta_text=row[13],
            likes=row[14],
            comments=row[15],
            shares=row[16],
            start_date=row[17],
            end_date=row[18],
            tags=row[19] if row[19] else [],
            landing_page_url=row[20],
            created_at=row[21],
            saved_at=row[22],
        )
        curators_raw = row[2] if row[2] else []
        curators = []
        for c in curators_raw:
            curators.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "avatar_url": c.get("avatar_url"),
                "added_at": c["added_at"] if isinstance(c["added_at"], str) else c["added_at"].isoformat(),
            })
        items.append({
            "ad_id": str(row[0]),
            "first_added_at": row[1].isoformat(),
            "curators": curators,
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
