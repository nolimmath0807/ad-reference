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

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2/research/adlib/ad/query/"

# WARNING: TikTok Commercial Content API currently provides EU data only.
# Non-EU regions may return empty or limited results.
EU_DATA_WARNING = (
    "TikTok Commercial Content API currently only supports EU data. "
    "Results for non-EU regions may be empty or limited."
)


def _normalize_tiktok_response(raw: dict) -> PlatformAd:
    ad_id = raw.get("ad_id", raw.get("id", ""))

    advertiser_name = raw.get("business_name", raw.get("advertiser_name", "Unknown"))

    ad_text = raw.get("ad_text", raw.get("ad_copy", None))

    media = raw.get("videos", [])
    thumbnail = ""
    preview_url = None
    media_type = "image"

    if media:
        first_video = media[0] if isinstance(media[0], dict) else {"url": media[0]}
        thumbnail = first_video.get("cover_image_url", first_video.get("thumbnail", ""))
        preview_url = first_video.get("url", None)
        media_type = "video"
    else:
        images = raw.get("images", [])
        if images:
            first_image = images[0] if isinstance(images[0], dict) else {"url": images[0]}
            thumbnail = first_image.get("url", first_image.get("image_url", ""))
            preview_url = thumbnail

    start_str = raw.get("first_shown_date", raw.get("start_date"))
    start_date = date.fromisoformat(start_str[:10]) if start_str else None

    end_str = raw.get("last_shown_date", raw.get("end_date"))
    end_date = date.fromisoformat(end_str[:10]) if end_str else None

    ad_format = "video" if media_type == "video" else "image"

    return PlatformAd(
        source_id=str(ad_id),
        platform=PlatformType.tiktok,
        format=ad_format,
        advertiser_name=advertiser_name,
        advertiser_handle=raw.get("advertiser_handle"),
        thumbnail_url=thumbnail,
        preview_url=preview_url,
        media_type=media_type,
        ad_copy=ad_text,
        cta_text=raw.get("cta_text"),
        start_date=start_date,
        end_date=end_date,
        landing_page_url=raw.get("landing_page_url"),
        tags=[],
        raw_data=raw,
    )


async def search_tiktok_ads(
    keyword: str,
    date_range: tuple[str, str] | None = None,
    limit: int = 25,
) -> list[PlatformAd]:
    api_key = os.environ["TIKTOK_API_KEY"]

    print(f"[WARNING] {EU_DATA_WARNING}")

    search_filters = {
        "ad_text": {"values": [keyword]},
    }

    if date_range:
        search_filters["start_date"] = {"min": date_range[0], "max": date_range[1]}

    payload = {
        "filters": search_filters,
        "max_count": limit,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TIKTOK_API_BASE, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("data", {}).get("ads", [])
    return [_normalize_tiktok_response(ad) for ad in ads_data]


async def get_tiktok_ad_detail(ad_id: str) -> PlatformAd | None:
    api_key = os.environ["TIKTOK_API_KEY"]

    payload = {
        "filters": {
            "ad_ids": {"values": [ad_id]},
        },
        "max_count": 1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TIKTOK_API_BASE, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("data", {}).get("ads", [])
    if not ads_data:
        return None

    return _normalize_tiktok_response(ads_data[0])


def main(keyword: str) -> dict:
    ads = asyncio.run(search_tiktok_ads(keyword))
    return {
        "platform": "tiktok",
        "keyword": keyword,
        "warning": EU_DATA_WARNING,
        "count": len(ads),
        "ads": [ad.model_dump(mode="json") for ad in ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Commercial Content API Client")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    args = parser.parse_args()

    result = main(args.keyword)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
