import argparse
import asyncio
import json
import os
from datetime import date, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from platforms.model import PlatformAd, PlatformType

load_dotenv()

META_API_BASE = "https://graph.facebook.com/v23.0"
META_AD_FIELDS = ",".join([
    "id",
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_snapshot_url",
    "page_name",
    "page_id",
    "publisher_platforms",
    "estimated_audience_size",
    "impressions",
    "spend",
    "currency",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
])


def _normalize_meta_response(raw: dict) -> PlatformAd:
    publisher_platforms = raw.get("publisher_platforms", [])
    if "instagram" in publisher_platforms and "facebook" not in publisher_platforms:
        platform = PlatformType.instagram
    else:
        platform = PlatformType.meta

    bodies = raw.get("ad_creative_bodies", [])
    ad_copy = bodies[0] if bodies else None

    titles = raw.get("ad_creative_link_titles", [])
    cta_text = titles[0] if titles else None

    start_str = raw.get("ad_delivery_start_time")
    start_date = date.fromisoformat(start_str[:10]) if start_str else None

    stop_str = raw.get("ad_delivery_stop_time")
    end_date = date.fromisoformat(stop_str[:10]) if stop_str else None

    snapshot_url = raw.get("ad_snapshot_url", "")

    return PlatformAd(
        source_id=raw.get("id", ""),
        platform=platform,
        format="image",
        advertiser_name=raw.get("page_name", "Unknown"),
        advertiser_handle=raw.get("page_id"),
        thumbnail_url=snapshot_url,
        preview_url=snapshot_url,
        media_type="image",
        ad_copy=ad_copy,
        cta_text=cta_text,
        start_date=start_date,
        end_date=end_date,
        landing_page_url=None,
        tags=[],
        raw_data=raw,
    )


async def search_meta_ads(
    keyword: str,
    country: str = "KR",
    ad_type: str = "ALL",
    limit: int = 25,
) -> list[PlatformAd]:
    access_token = os.environ["META_ACCESS_TOKEN"]

    params = {
        "access_token": access_token,
        "search_terms": keyword,
        "ad_reached_countries": f'["{country}"]',
        "ad_type": ad_type,
        "fields": META_AD_FIELDS,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{META_API_BASE}/ads_archive", params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            await asyncio.sleep(retry_after)
            resp = await client.get(f"{META_API_BASE}/ads_archive", params=params)

        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("data", [])
    return [_normalize_meta_response(ad) for ad in ads_data]


async def get_meta_ad_detail(ad_id: str) -> PlatformAd | None:
    access_token = os.environ["META_ACCESS_TOKEN"]

    params = {
        "access_token": access_token,
        "search_terms": "",
        "ad_reached_countries": '["KR"]',
        "fields": META_AD_FIELDS,
        "search_page_ids": ad_id,
        "limit": 1,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{META_API_BASE}/ads_archive", params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            await asyncio.sleep(retry_after)
            resp = await client.get(f"{META_API_BASE}/ads_archive", params=params)

        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("data", [])
    if not ads_data:
        return None

    return _normalize_meta_response(ads_data[0])


def main(keyword: str) -> dict:
    ads = asyncio.run(search_meta_ads(keyword))
    return {
        "platform": "meta",
        "keyword": keyword,
        "count": len(ads),
        "ads": [ad.model_dump(mode="json") for ad in ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta Ad Library API Client")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    args = parser.parse_args()

    result = main(args.keyword)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"meta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
