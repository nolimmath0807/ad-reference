import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db
from ads.model import Ad, AdDetailResponse


AD_COLUMNS = """
    id, platform, format, advertiser_name, advertiser_handle,
    advertiser_avatar_url, thumbnail_url, preview_url, media_type,
    ad_copy, cta_text, likes, comments, shares,
    start_date, end_date, tags, landing_page_url,
    created_at, saved_at
"""


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


def get_ad_detail(ad_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            f"SELECT {AD_COLUMNS} FROM ads WHERE id = %s",
            (ad_id,),
        )
        col_names = [desc[0] for desc in cur.description]
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Ad not found")

        ad = _row_to_ad(row, col_names)

        # Similar ads: same advertiser_name OR same (platform, format), exclude self, limit 6
        cur.execute(
            f"""
            SELECT {AD_COLUMNS}
            FROM ads
            WHERE id != %s
              AND (advertiser_name = %s OR (platform = %s AND format = %s))
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (ad_id, ad.advertiser_name, ad.platform.value, ad.format.value),
        )
        col_names_similar = [desc[0] for desc in cur.description]
        similar_rows = cur.fetchall()
        similar_ads = [_row_to_ad(r, col_names_similar) for r in similar_rows]

    resp = AdDetailResponse(ad=ad, similar_ads=similar_ads)
    return resp.model_dump(mode="json")


def main(ad_id: str) -> dict:
    return get_ad_detail(ad_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get ad detail by ID")
    parser.add_argument("--ad-id", required=True, help="Ad UUID")
    args = parser.parse_args()

    result = main(args.ad_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
