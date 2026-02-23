import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from conn import get_db
from platforms.meta import search_meta_ads
from platforms.google import search_google_ads
from platforms.tiktok import search_tiktok_ads
from platforms.model import PlatformAd

load_dotenv()

_scheduler: BackgroundScheduler | None = None


def _save_ads_to_db(ads: list[PlatformAd]) -> int:
    if not ads:
        return 0

    saved_count = 0
    with get_db() as (conn, cur):
        for ad in ads:
            cur.execute(
                """
                INSERT INTO ads (
                    source_id, platform, format, advertiser_name,
                    advertiser_handle, thumbnail_url, preview_url,
                    media_type, ad_copy, cta_text,
                    start_date, end_date, tags,
                    landing_page_url, raw_data
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (source_id, platform) DO UPDATE SET
                    advertiser_name = EXCLUDED.advertiser_name,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    preview_url = EXCLUDED.preview_url,
                    ad_copy = EXCLUDED.ad_copy,
                    cta_text = EXCLUDED.cta_text,
                    end_date = EXCLUDED.end_date,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = NOW()
                """,
                (
                    ad.source_id,
                    ad.platform.value,
                    ad.format,
                    ad.advertiser_name,
                    ad.advertiser_handle,
                    ad.thumbnail_url,
                    ad.preview_url,
                    ad.media_type,
                    ad.ad_copy,
                    ad.cta_text,
                    ad.start_date.isoformat() if ad.start_date else None,
                    ad.end_date.isoformat() if ad.end_date else None,
                    ad.tags,
                    ad.landing_page_url,
                    json.dumps(ad.raw_data, ensure_ascii=False, default=str),
                ),
            )
            saved_count += 1

    return saved_count


def collect_ads_job(keywords: list[str]) -> dict:
    all_ads: list[PlatformAd] = []
    results = {"meta": 0, "google": 0, "tiktok": 0, "errors": []}

    for keyword in keywords:
        # Meta
        meta_ads = asyncio.run(search_meta_ads(keyword))
        all_ads.extend(meta_ads)
        results["meta"] += len(meta_ads)

        # Google
        google_ads = asyncio.run(search_google_ads(keyword))
        all_ads.extend(google_ads)
        results["google"] += len(google_ads)

        # TikTok
        tiktok_ads = asyncio.run(search_tiktok_ads(keyword))
        all_ads.extend(tiktok_ads)
        results["tiktok"] += len(tiktok_ads)

    saved = _save_ads_to_db(all_ads)
    results["total_collected"] = len(all_ads)
    results["total_saved"] = saved
    results["collected_at"] = datetime.now().isoformat()

    print(f"[Scheduler] Collected {len(all_ads)} ads, saved {saved} to DB")
    return results


def start_scheduler(
    keywords: list[str],
    interval_hours: int = 6,
) -> BackgroundScheduler:
    global _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        collect_ads_job,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[keywords],
        id="ad_collection_job",
        name="Ad Data Auto-Collection",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[Scheduler] Started - collecting every {interval_hours} hours for keywords: {keywords}")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")
    _scheduler = None


def main(keywords: list[str]) -> dict:
    print(f"[Scheduler] Running one-time collection for keywords: {keywords}")
    result = collect_ads_job(keywords)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ad Data Auto-Collection Scheduler")
    parser.add_argument(
        "--keywords",
        required=True,
        nargs="+",
        help="Keywords to collect ads for",
    )
    args = parser.parse_args()

    result = main(args.keywords)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"scheduler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
