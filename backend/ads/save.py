import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from conn import get_db
from ads.model import Ad, AdSaveRequest


def save_ad(request: AdSaveRequest) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO ads (
                platform, format, advertiser_name, advertiser_handle,
                advertiser_avatar_url, thumbnail_url, preview_url, media_type,
                ad_copy, cta_text, likes, comments, shares,
                start_date, end_date, tags, landing_page_url, saved_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, NOW()
            )
            RETURNING id, platform, format, advertiser_name, advertiser_handle,
                      advertiser_avatar_url, thumbnail_url, preview_url, media_type,
                      ad_copy, cta_text, likes, comments, shares,
                      start_date, end_date, tags, landing_page_url,
                      created_at, saved_at
            """,
            (
                request.platform.value,
                request.format.value,
                request.advertiser_name,
                request.advertiser_handle,
                request.advertiser_avatar_url,
                request.thumbnail_url,
                request.preview_url,
                request.media_type.value,
                request.ad_copy,
                request.cta_text,
                request.likes,
                request.comments,
                request.shares,
                request.start_date,
                request.end_date,
                request.tags,
                request.landing_page_url,
            ),
        )
        col_names = [desc[0] for desc in cur.description]
        row = cur.fetchone()

    d = dict(zip(col_names, row))
    ad = Ad(
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
    return ad.model_dump(mode="json")


def main(
    platform: str,
    format: str,
    advertiser_name: str,
    thumbnail_url: str,
    media_type: str,
    advertiser_handle: str = None,
    advertiser_avatar_url: str = None,
    preview_url: str = None,
    ad_copy: str = None,
    cta_text: str = None,
    likes: int = None,
    comments: int = None,
    shares: int = None,
    start_date: str = None,
    end_date: str = None,
    tags: list[str] = None,
    landing_page_url: str = None,
) -> dict:
    from datetime import date as date_type

    request = AdSaveRequest(
        platform=platform,
        format=format,
        advertiser_name=advertiser_name,
        thumbnail_url=thumbnail_url,
        media_type=media_type,
        advertiser_handle=advertiser_handle,
        advertiser_avatar_url=advertiser_avatar_url,
        preview_url=preview_url,
        ad_copy=ad_copy,
        cta_text=cta_text,
        likes=likes,
        comments=comments,
        shares=shares,
        start_date=date_type.fromisoformat(start_date) if start_date else None,
        end_date=date_type.fromisoformat(end_date) if end_date else None,
        tags=tags or [],
        landing_page_url=landing_page_url,
    )
    return save_ad(request)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save an ad to DB")
    parser.add_argument("--platform", required=True, help="Platform (meta|google|tiktok|instagram)")
    parser.add_argument("--format", required=True, help="Format (image|video|carousel|reels)")
    parser.add_argument("--advertiser-name", required=True, help="Advertiser name")
    parser.add_argument("--thumbnail-url", required=True, help="Thumbnail URL")
    parser.add_argument("--media-type", required=True, help="Media type (image|video)")
    parser.add_argument("--advertiser-handle", default=None, help="Advertiser handle")
    parser.add_argument("--advertiser-avatar-url", default=None, help="Advertiser avatar URL")
    parser.add_argument("--preview-url", default=None, help="Preview URL")
    parser.add_argument("--ad-copy", default=None, help="Ad copy text")
    parser.add_argument("--cta-text", default=None, help="CTA button text")
    parser.add_argument("--likes", type=int, default=None, help="Likes count")
    parser.add_argument("--comments", type=int, default=None, help="Comments count")
    parser.add_argument("--shares", type=int, default=None, help="Shares count")
    parser.add_argument("--start-date", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--tags", nargs="*", default=None, help="Tag list")
    parser.add_argument("--landing-page-url", default=None, help="Landing page URL")
    args = parser.parse_args()

    result = main(
        platform=args.platform,
        format=args.format,
        advertiser_name=args.advertiser_name,
        thumbnail_url=args.thumbnail_url,
        media_type=args.media_type,
        advertiser_handle=args.advertiser_handle,
        advertiser_avatar_url=args.advertiser_avatar_url,
        preview_url=args.preview_url,
        ad_copy=args.ad_copy,
        cta_text=args.cta_text,
        likes=args.likes,
        comments=args.comments,
        shares=args.shares,
        start_date=args.start_date,
        end_date=args.end_date,
        tags=args.tags,
        landing_page_url=args.landing_page_url,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
