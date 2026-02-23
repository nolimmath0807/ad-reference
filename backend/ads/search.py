import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from conn import get_db
from ads.model import Ad, AdSearchResponse, Platform, Format
from platforms.meta import search_meta_ads
from platforms.google import search_google_ads
from platforms.tiktok import search_tiktok_ads
from platforms.model import PlatformAd


def _row_to_ad(row: tuple, col_names: list[str]) -> Ad:
    d = dict(zip(col_names, row))
    return Ad(
        id=str(d["id"]),
        platform=d["platform"],
        format=d["format"],
        advertiser_name=d["advertiser_name"],
        advertiser_handle=d.get("advertiser_handle"),
        advertiser_avatar_url=d.get("advertiser_avatar_url"),
        thumbnail_url=d["thumbnail_url"],
        preview_url=d.get("preview_url"),
        media_type=d["media_type"],
        ad_copy=d.get("ad_copy"),
        cta_text=d.get("cta_text"),
        likes=d.get("likes"),
        comments=d.get("comments"),
        shares=d.get("shares"),
        start_date=d.get("start_date"),
        end_date=d.get("end_date"),
        tags=d.get("tags", []),
        landing_page_url=d.get("landing_page_url"),
        created_at=d["created_at"],
        saved_at=d.get("saved_at"),
    )


def _platform_ad_to_ad(pad: PlatformAd, ad_id: str, created_at: datetime) -> Ad:
    return Ad(
        id=ad_id,
        platform=pad.platform.value,
        format=pad.format,
        advertiser_name=pad.advertiser_name,
        advertiser_handle=pad.advertiser_handle,
        thumbnail_url=pad.thumbnail_url,
        preview_url=pad.preview_url,
        media_type=pad.media_type,
        ad_copy=pad.ad_copy,
        cta_text=pad.cta_text,
        likes=pad.likes,
        comments=pad.comments,
        shares=pad.shares,
        start_date=pad.start_date,
        end_date=pad.end_date,
        tags=pad.tags,
        landing_page_url=pad.landing_page_url,
        created_at=created_at,
    )


def _insert_platform_ad(conn, cur, pad: PlatformAd) -> Ad:
    cur.execute(
        """
        INSERT INTO ads (
            platform, format, advertiser_name, advertiser_handle,
            thumbnail_url, preview_url, media_type, ad_copy, cta_text,
            likes, comments, shares, start_date, end_date,
            tags, landing_page_url, source_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (source_id, platform) DO UPDATE SET id = ads.id
        RETURNING id, created_at
        """,
        (
            pad.platform.value, pad.format, pad.advertiser_name,
            pad.advertiser_handle, pad.thumbnail_url, pad.preview_url,
            pad.media_type, pad.ad_copy, pad.cta_text,
            pad.likes, pad.comments, pad.shares,
            pad.start_date, pad.end_date,
            pad.tags, pad.landing_page_url, pad.source_id,
        ),
    )
    row = cur.fetchone()
    conn.commit()
    return _platform_ad_to_ad(pad, str(row[0]), row[1])


def _build_where(
    keyword: Optional[str],
    platform: str,
    format: str,
    date_from: Optional[str],
    date_to: Optional[str],
    industry: Optional[str],
) -> tuple[str, list]:
    conditions = []
    params = []

    if keyword:
        conditions.append("(advertiser_name ILIKE %s OR ad_copy ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if platform != "all":
        conditions.append("platform = %s")
        params.append(platform)

    if format != "all":
        conditions.append("format = %s")
        params.append(format)

    if date_from:
        conditions.append("start_date >= %s")
        params.append(date_from)

    if date_to:
        conditions.append("(end_date <= %s OR end_date IS NULL)")
        params.append(date_to)

    if industry:
        conditions.append("%s = ANY(tags)")
        params.append(industry)

    conditions.append("format != 'text'")

    where = " AND ".join(conditions) if conditions else "TRUE"
    return where, params


def _sort_clause(sort: str) -> str:
    if sort == "popular":
        return "COALESCE(likes, 0) DESC"
    if sort == "engagement":
        return "(COALESCE(likes, 0) + COALESCE(comments, 0) + COALESCE(shares, 0)) DESC"
    return "created_at DESC"


async def _fetch_from_platforms(
    keyword: str,
    platform: str,
    limit: int,
) -> list[PlatformAd]:
    results: list[PlatformAd] = []

    targets = []
    if platform in ("all", "meta", "instagram"):
        targets.append("meta")
    if platform in ("all", "google"):
        targets.append("google")
    if platform in ("all", "tiktok"):
        targets.append("tiktok")

    per_platform = max(limit // len(targets), 5) if targets else limit

    tasks = []
    for t in targets:
        if t == "meta":
            tasks.append(search_meta_ads(keyword, limit=per_platform))
        elif t == "google":
            tasks.append(search_google_ads(keyword, limit=per_platform))
        elif t == "tiktok":
            tasks.append(search_tiktok_ads(keyword, limit=per_platform))

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for res in gathered:
        if isinstance(res, list):
            results.extend(res)

    return results


async def search_ads(
    keyword: Optional[str],
    platform: str,
    format: str,
    sort: str,
    date_from: Optional[str],
    date_to: Optional[str],
    industry: Optional[str],
    page: int,
    limit: int,
) -> dict:
    where, params = _build_where(keyword, platform, format, date_from, date_to, industry)
    order = _sort_clause(sort)
    offset = (page - 1) * limit

    with get_db() as (conn, cur):
        # Count total
        cur.execute(f"SELECT COUNT(*) FROM ads WHERE {where}", params)
        total = cur.fetchone()[0]

        # Fetch page
        cur.execute(
            f"""
            SELECT id, platform, format, advertiser_name, advertiser_handle,
                   advertiser_avatar_url, thumbnail_url, preview_url, media_type,
                   ad_copy, cta_text, likes, comments, shares,
                   start_date, end_date, tags, landing_page_url,
                   created_at, saved_at
            FROM ads
            WHERE {where}
            ORDER BY {order}
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        col_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        items = [_row_to_ad(r, col_names) for r in rows]

        # If DB results insufficient and keyword provided, fetch from platforms
        if len(items) < limit and keyword and page == 1:
            needed = limit - len(items)
            platform_ads = await _fetch_from_platforms(keyword, platform, needed)

            for pad in platform_ads[:needed]:
                ad = _insert_platform_ad(conn, cur, pad)
                items.append(ad)

            total += len(platform_ads[:needed])

    resp = AdSearchResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total,
    )
    return resp.model_dump(mode="json")


def main(
    keyword: Optional[str],
    platform: str,
    format: str,
    sort: str,
    date_from: Optional[str],
    date_to: Optional[str],
    industry: Optional[str],
    page: int,
    limit: int,
) -> dict:
    return asyncio.run(search_ads(keyword, platform, format, sort, date_from, date_to, industry, page, limit))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search ads across platforms")
    parser.add_argument("--keyword", default=None, help="Search keyword")
    parser.add_argument("--platform", default="all", help="Platform filter (all|meta|google|tiktok|instagram)")
    parser.add_argument("--format", default="all", help="Format filter (all|image|video|carousel|reels)")
    parser.add_argument("--sort", default="recent", help="Sort order (recent|popular|engagement)")
    parser.add_argument("--date-from", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--industry", default=None, help="Industry tag filter")
    parser.add_argument("--page", type=int, default=1, help="Page number")
    parser.add_argument("--limit", type=int, default=20, help="Items per page")
    args = parser.parse_args()

    result = main(
        args.keyword, args.platform, args.format, args.sort,
        args.date_from, args.date_to, args.industry,
        args.page, args.limit,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
