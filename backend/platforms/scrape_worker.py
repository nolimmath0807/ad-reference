import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from conn import get_db
from platforms.model import PlatformAd
from platforms.s3 import is_s3_configured, upload_from_url
from platforms.meta_scraper import scrape_meta_ads
from platforms.google_scraper import scrape_google_ads_by_keyword, scrape_google_ads_by_domain
from utils.activity_log import log_activity


logger = logging.getLogger("scrape_worker")


def _upload_ad_media_to_s3(ad: PlatformAd, s3_prefix: str) -> dict:
    """Upload thumbnail_url and preview_url to S3, replace URLs in-place. Returns stats."""
    stats = {"success": 0, "failed": 0}

    if ad.thumbnail_url:
        s3_url = upload_from_url(ad.thumbnail_url, f"{s3_prefix}/thumb")
        if s3_url:
            ad.thumbnail_url = s3_url
            stats["success"] += 1
        else:
            stats["failed"] += 1

    if ad.preview_url and ad.preview_url != ad.thumbnail_url:
        s3_url = upload_from_url(ad.preview_url, f"{s3_prefix}/preview")
        if s3_url:
            ad.preview_url = s3_url
            stats["success"] += 1
        else:
            stats["failed"] += 1

    return stats


def _save_ads_to_db(ads: list[PlatformAd]) -> int:
    """Save ads to database with UPSERT. Returns number saved."""
    if not ads:
        return 0

    saved = 0
    with get_db() as (conn, cur):
        for ad in ads:
            cur.execute(
                """
                INSERT INTO ads (
                    source_id, platform, format, advertiser_name,
                    advertiser_handle, thumbnail_url, preview_url,
                    media_type, ad_copy, cta_text,
                    start_date, end_date, tags,
                    landing_page_url, domain,
                    saved_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    NOW()
                )
                ON CONFLICT (source_id, platform) DO UPDATE SET
                    advertiser_name = EXCLUDED.advertiser_name,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    preview_url = EXCLUDED.preview_url,
                    ad_copy = EXCLUDED.ad_copy,
                    domain = EXCLUDED.domain,
                    saved_at = NOW()
                """,
                (
                    ad.source_id, ad.platform.value, ad.format,
                    ad.advertiser_name, ad.advertiser_handle,
                    ad.thumbnail_url, ad.preview_url,
                    ad.media_type, ad.ad_copy, ad.cta_text,
                    ad.start_date, ad.end_date,
                    ad.tags, ad.landing_page_url,
                    ad.domain,
                ),
            )
            saved += 1

    return saved


def upsert_ads_batch(ads: list[PlatformAd], brand_id: str | None = None) -> dict:
    """광고를 DB에 UPSERT하고 신규/업데이트 건수를 반환.

    Args:
        ads: List of PlatformAd objects to upsert.
        brand_id: Optional brand_id to set on all ads. If provided, overrides ad.brand_id.

    Returns: {"new": int, "updated": int, "total": int}
    """
    if not ads:
        return {"new": 0, "updated": 0, "total": 0}

    new = 0
    updated = 0

    with get_db() as (conn, cur):
        for ad in ads:
            effective_brand_id = brand_id or ad.brand_id
            cur.execute(
                """
                INSERT INTO ads (
                    source_id, platform, format, advertiser_name,
                    advertiser_handle, thumbnail_url, preview_url,
                    media_type, ad_copy, cta_text,
                    start_date, end_date, tags,
                    landing_page_url, raw_data, domain, creative_id,
                    brand_id, saved_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, NOW()
                )
                ON CONFLICT (source_id, platform) DO UPDATE SET
                    advertiser_name = EXCLUDED.advertiser_name,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    preview_url = EXCLUDED.preview_url,
                    ad_copy = EXCLUDED.ad_copy,
                    cta_text = EXCLUDED.cta_text,
                    end_date = EXCLUDED.end_date,
                    raw_data = EXCLUDED.raw_data,
                    landing_page_url = EXCLUDED.landing_page_url,
                    domain = EXCLUDED.domain,
                    creative_id = COALESCE(EXCLUDED.creative_id, ads.creative_id),
                    brand_id = COALESCE(EXCLUDED.brand_id, ads.brand_id),
                    updated_at = NOW(),
                    saved_at = NOW()
                RETURNING (xmax = 0) AS is_new
                """,
                (
                    ad.source_id, ad.platform.value, ad.format,
                    ad.advertiser_name, ad.advertiser_handle,
                    ad.thumbnail_url, ad.preview_url,
                    ad.media_type, ad.ad_copy, ad.cta_text,
                    ad.start_date, ad.end_date,
                    ad.tags, ad.landing_page_url,
                    json.dumps(ad.raw_data, ensure_ascii=False, default=str),
                    ad.domain, ad.creative_id,
                    effective_brand_id,
                ),
            )
            is_new = cur.fetchone()[0]
            if is_new:
                new += 1
            else:
                updated += 1

    total = new + updated
    logger.info(f"UPSERT 완료: new={new}, updated={updated}, total={total}")
    if new > 0:
        log_activity(
            event_type="ad_change",
            event_subtype="new_ads_found",
            title=f"{new} new ads saved",
            metadata={"new": new, "updated": updated, "brand_id": brand_id},
        )
    return {"new": new, "updated": updated, "total": total}


def run_crawl(keyword: str, platforms: list[str], search_type: str = "keyword", max_results: int = 12) -> dict:
    result = {
        "keyword": keyword,
        "platforms": platforms,
        "results": {},
        "total_scraped": 0,
        "total_saved": 0,
        "s3_uploads": {"success": 0, "failed": 0},
        "errors": [],
    }

    all_ads: list[PlatformAd] = []

    for platform in platforms:
        scraped_ads: list[PlatformAd] = []

        if platform == "meta":
            logger.info(f"Meta 스크래핑 시작: keyword='{keyword}'")
            try:
                scraped_ads = scrape_meta_ads(keyword, headless=True, max_results=max_results)
            except Exception as e:
                error_msg = f"meta scrape failed: {type(e).__name__}: {e}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        elif platform == "google":
            if search_type == "domain":
                logger.info(f"Google 도메인 스크래핑 시작: domain='{keyword}'")
                try:
                    scraped_ads = scrape_google_ads_by_domain(keyword, headless=True, max_results=max_results)
                except Exception as e:
                    error_msg = f"google domain scrape failed: {type(e).__name__}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            else:
                logger.info(f"Google 키워드 스크래핑 시작: keyword='{keyword}'")
                try:
                    scraped_ads = scrape_google_ads_by_keyword(keyword, headless=True, max_results=max_results)
                except Exception as e:
                    error_msg = f"google scrape failed: {type(e).__name__}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

        logger.info(f"[{platform}] {len(scraped_ads)}건 스크래핑 완료")

        # S3 upload (optional)
        if is_s3_configured():
            s3_prefix = f"ads/{platform}/{keyword}"
            for ad in scraped_ads:
                stats = _upload_ad_media_to_s3(ad, s3_prefix)
                result["s3_uploads"]["success"] += stats["success"]
                result["s3_uploads"]["failed"] += stats["failed"]

        # DB save
        saved_count = _save_ads_to_db(scraped_ads)

        result["results"][platform] = {
            "scraped": len(scraped_ads),
            "saved": saved_count,
        }
        result["total_scraped"] += len(scraped_ads)
        result["total_saved"] += saved_count
        all_ads.extend(scraped_ads)

    logger.info(f"전체 완료: scraped={result['total_scraped']}, saved={result['total_saved']}")
    return result


def main(keyword: str, platforms: list[str], max_results: int = 12) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    return run_crawl(keyword, platforms, max_results=max_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified scrape worker: scrape -> S3 upload -> DB save")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--platforms", nargs="+", choices=["meta", "google"], default=["meta", "google"], help="Platforms to scrape")
    parser.add_argument("--max-results", type=int, default=12, help="Maximum results per platform")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (default: True)")
    args = parser.parse_args()

    result = main(args.keyword, args.platforms, max_results=args.max_results)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"scrape_worker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
