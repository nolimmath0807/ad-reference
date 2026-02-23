import argparse
import asyncio
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from platforms.model import PlatformAd, PlatformType

load_dotenv()

SERPAPI_BASE = "https://serpapi.com/search"

# Simple in-memory cache: key -> (timestamp, data)
_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300  # 5 minutes


def _get_cached(cache_key: str) -> list[dict] | None:
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _cache[cache_key]
    return None


def _set_cache(cache_key: str, data: list[dict]) -> None:
    _cache[cache_key] = (time.time(), data)


def _unix_to_date(ts: int | float | None) -> date | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts).date()


def _normalize_google_response(raw: dict) -> PlatformAd:
    source_id = raw.get("ad_creative_id", str(hash(json.dumps(raw, sort_keys=True, default=str))))
    advertiser_name = raw.get("advertiser", "Unknown")
    advertiser_handle = raw.get("advertiser_id", None)

    thumbnail = raw.get("image", "")
    preview_url = raw.get("details_link", None)

    ad_format = raw.get("format", "image").lower()
    if ad_format not in ("text", "image", "video"):
        ad_format = "image"

    media_type = "video" if ad_format == "video" else "image"

    start_date = _unix_to_date(raw.get("first_shown"))
    end_date = _unix_to_date(raw.get("last_shown"))

    target_domain = raw.get("target_domain", None)
    landing_page_url = None
    if target_domain:
        landing_page_url = target_domain if target_domain.startswith("http") else f"https://{target_domain}"

    return PlatformAd(
        source_id=str(source_id),
        platform=PlatformType.google,
        format=ad_format,
        advertiser_name=advertiser_name,
        advertiser_handle=advertiser_handle,
        thumbnail_url=thumbnail,
        preview_url=preview_url,
        media_type=media_type,
        ad_copy=None,
        cta_text=None,
        start_date=start_date,
        end_date=end_date,
        landing_page_url=landing_page_url,
        tags=[],
        raw_data=raw,
    )


async def search_google_ads(
    keyword: str,
    format: str | None = None,
    limit: int = 25,
) -> list[PlatformAd]:
    cache_key = f"google:{keyword}:{format}:{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return [_normalize_google_response(ad) for ad in cached]

    api_key = os.environ["SERPAPI_KEY"]

    params = {
        "engine": "google_ads_transparency_center",
        "text": keyword,
        "api_key": api_key,
        "num": min(limit, 100),
    }
    if format:
        params["creative_format"] = format

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("ad_creatives", [])[:limit]
    _set_cache(cache_key, ads_data)

    results = [_normalize_google_response(ad) for ad in ads_data]
    return [ad for ad in results if ad.format != 'text']


async def get_google_ad_detail(advertiser_id: str, creative_id: str | None = None) -> PlatformAd | None:
    api_key = os.environ["SERPAPI_KEY"]

    params: dict[str, str] = {
        "engine": "google_ads_transparency_center",
        "advertiser_id": advertiser_id,
        "api_key": api_key,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    ads_data = data.get("ad_creatives", [])
    if not ads_data:
        return None

    if creative_id:
        for ad in ads_data:
            if ad.get("ad_creative_id") == creative_id:
                return _normalize_google_response(ad)

    return _normalize_google_response(ads_data[0])


def main(keyword: str) -> dict:
    ads = asyncio.run(search_google_ads(keyword))
    return {
        "platform": "google",
        "keyword": keyword,
        "count": len(ads),
        "ads": [ad.model_dump(mode="json") for ad in ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Ads Transparency Center Client (SerpApi)")
    parser.add_argument("--keyword", required=True, help="Search keyword (domain or text, e.g. nike.com)")
    args = parser.parse_args()

    result = main(args.keyword)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"google_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
