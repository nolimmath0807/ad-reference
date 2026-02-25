import argparse
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from conn import get_db
from platforms.google_scraper import scrape_google_ads_by_domain
from platforms.model import BatchRunStatus, BrandSourceScrapeResult, DomainScrapeResult, MonitoredDomain
from platforms.scrape_worker import upsert_ads_batch
from utils.activity_log import log_activity
from utils.daily_stats import record_daily_stats

logger = logging.getLogger("batch_collector")


def get_active_domains() -> list[MonitoredDomain]:
    """monitored_domains 테이블에서 is_active=True인 도메인 조회"""
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, domain, platform, is_active, notes, created_at, updated_at
            FROM monitored_domains
            WHERE is_active = TRUE
            ORDER BY created_at
            """
        )
        rows = cur.fetchall()

    domains = []
    for row in rows:
        domains.append(
            MonitoredDomain(
                id=str(row[0]),
                domain=row[1],
                platform=row[2],
                is_active=row[3],
                notes=row[4],
                created_at=row[5],
                updated_at=row[6],
            )
        )
    return domains


def get_active_brand_sources() -> list[dict]:
    """brands + brand_sources JOIN, both is_active=True"""
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT bs.id, bs.brand_id, b.brand_name, bs.platform, bs.source_type, bs.source_value
            FROM brand_sources bs
            JOIN brands b ON b.id = bs.brand_id
            WHERE bs.is_active = TRUE AND b.is_active = TRUE
            ORDER BY b.brand_name, bs.platform
        """)
        rows = cur.fetchall()
    return [
        {
            "source_id": str(r[0]),
            "brand_id": str(r[1]),
            "brand_name": r[2],
            "platform": r[3],
            "source_type": r[4],
            "source_value": r[5],
        }
        for r in rows
    ]


def scrape_source(source: dict, mode: str = "full") -> BrandSourceScrapeResult:
    """Dispatch scraping by platform and source_type."""
    start_time = time.monotonic()
    platform = source["platform"]
    source_type = source["source_type"]
    source_value = source["source_value"]
    brand_id = source["brand_id"]

    result = BrandSourceScrapeResult(
        source_id=source["source_id"],
        platform=platform,
        source_type=source_type,
        source_value=source_value,
    )

    def on_batch(ads):
        for ad in ads:
            if not ad.domain:
                ad.domain = source_value
            ad.brand_id = brand_id
        stats = upsert_ads_batch(ads, brand_id=brand_id)
        result.ads_scraped += len(ads)
        result.ads_new += stats["new"]
        result.ads_updated += stats["updated"]

    if platform == "google" and source_type == "domain":
        scrape_google_ads_by_domain(
            domain=source_value,
            headless=True,
            max_results=None,
            on_batch_callback=on_batch,
            mode="incremental" if mode == "incremental" else "full",
        )
    elif platform == "meta" and source_type == "page_id":
        from platforms.meta_scraper import scrape_meta_ads_by_page_id, parse_meta_page_id
        page_id = parse_meta_page_id(source_value)
        ads = scrape_meta_ads_by_page_id(page_id, headless=True, max_results=30)
        if ads:
            on_batch(ads)
    elif platform == "meta" and source_type == "keyword":
        from platforms.meta_scraper import scrape_meta_ads
        ads = scrape_meta_ads(source_value, headless=True)
        if ads:
            on_batch(ads)
    elif platform == "tiktok" and source_type == "keyword":
        logger.info(f"TikTok scraping not yet implemented for: {source_value}")

    result.duration_seconds = round(time.monotonic() - start_time, 1)
    logger.info(
        f"[{source['brand_name']}:{platform}:{source_value}] "
        f"scraped={result.ads_scraped}, new={result.ads_new}, "
        f"updated={result.ads_updated}, duration={result.duration_seconds}s"
    )
    if result.ads_new > 0:
        log_activity(
            event_type="ad_change",
            event_subtype="new_ads_found",
            title=f"{result.ads_new} new ads from {source.get('brand_name', '')}",
            message=f"Platform: {platform}, Source: {source_value}",
            metadata={
                "brand_name": source.get("brand_name", ""),
                "platform": platform,
                "ads_new": result.ads_new,
                "ads_scraped": result.ads_scraped,
            },
        )
    if result.ads_new > 0 or result.ads_updated > 0:
        record_daily_stats(
            brand_id=brand_id,
            platform=platform,
            new_count=result.ads_new,
            updated_count=result.ads_updated,
            total_scraped=result.ads_scraped,
        )
    return result


def create_batch_run(trigger_type: str = "manual") -> str:
    """batch_runs 레코드 생성, UUID 반환"""
    run_id = str(uuid.uuid4())
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO batch_runs (id, started_at, status, trigger_type)
            VALUES (%s, NOW(), %s, %s)
            """,
            (run_id, BatchRunStatus.running.value, trigger_type),
        )
    logger.info(f"batch_run 생성: id={run_id}, trigger_type={trigger_type}")
    log_activity(
        event_type="collection",
        event_subtype="batch_started",
        title="Batch collection started",
        metadata={"trigger_type": trigger_type, "batch_run_id": run_id},
    )
    return run_id


def update_batch_run(run_id: str, **kwargs):
    """batch_runs 레코드 업데이트 (status, finished_at, totals, domain_results, errors)"""
    set_clauses = []
    values = []

    field_map = {
        "status": "status",
        "finished_at": "finished_at",
        "total_domains": "total_domains",
        "total_ads_scraped": "total_ads_scraped",
        "total_ads_new": "total_ads_new",
        "total_ads_updated": "total_ads_updated",
        "domain_results": "domain_results",
        "errors": "errors",
    }

    for key, column in field_map.items():
        if key in kwargs:
            val = kwargs[key]
            if key == "status" and isinstance(val, BatchRunStatus):
                val = val.value
            if key in ("domain_results", "errors"):
                val = json.dumps(val, ensure_ascii=False, default=str)
            set_clauses.append(f"{column} = %s")
            values.append(val)

    if not set_clauses:
        return

    values.append(run_id)
    with get_db() as (conn, cur):
        cur.execute(
            f"UPDATE batch_runs SET {', '.join(set_clauses)} WHERE id = %s",
            values,
        )


def scrape_domain_fully(domain: str) -> DomainScrapeResult:
    """단일 도메인 전체 스크래핑.
    - scrape_google_ads_by_domain 호출
    - on_batch_callback으로 50건마다 upsert_ads_batch() 호출하여 DB 저장
    - 도메인 레벨 통계(scraped, new, updated, duration) 반환
    """
    start_time = time.monotonic()
    result = DomainScrapeResult(domain=domain)

    def on_batch(ads):
        """50건마다 호출되는 콜백"""
        for ad in ads:
            if not ad.domain:
                ad.domain = domain
        stats = upsert_ads_batch(ads)
        result.ads_scraped += len(ads)
        result.ads_new += stats["new"]
        result.ads_updated += stats["updated"]
        logger.info(
            f"[{domain}] 배치 저장: +{len(ads)}건 "
            f"(누적: scraped={result.ads_scraped}, new={result.ads_new})"
        )

    scrape_google_ads_by_domain(
        domain=domain,
        headless=True,
        max_results=None,
        on_batch_callback=on_batch,
    )

    result.duration_seconds = round(time.monotonic() - start_time, 1)
    logger.info(
        f"[{domain}] 완료: scraped={result.ads_scraped}, "
        f"new={result.ads_new}, updated={result.ads_updated}, "
        f"duration={result.duration_seconds}s"
    )
    return result


def scrape_domain_incremental(domain: str) -> DomainScrapeResult:
    """단일 도메인 증분 스크래핑 - 새로운 creative만 상세 페이지 방문."""
    start_time = time.monotonic()
    result = DomainScrapeResult(domain=domain)

    def on_batch(ads):
        for ad in ads:
            if not ad.domain:
                ad.domain = domain
        stats = upsert_ads_batch(ads)
        result.ads_scraped += len(ads)
        result.ads_new += stats["new"]
        result.ads_updated += stats["updated"]
        logger.info(
            f"[{domain}] 증분 배치 저장: +{len(ads)}건 "
            f"(누적: scraped={result.ads_scraped}, new={result.ads_new})"
        )

    scrape_google_ads_by_domain(
        domain=domain,
        headless=True,
        max_results=None,
        on_batch_callback=on_batch,
        mode="incremental",
    )

    result.duration_seconds = round(time.monotonic() - start_time, 1)
    logger.info(
        f"[{domain}] 증분 완료: scraped={result.ads_scraped}, "
        f"new={result.ads_new}, updated={result.ads_updated}, "
        f"duration={result.duration_seconds}s"
    )
    return result


def _run_brand_sources_batch(run_id: str, brand_sources: list[dict], mode: str) -> dict:
    """Brand sources 기반 배치 수집 실행."""
    total_scraped = 0
    total_new = 0
    total_updated = 0
    domain_results = {}
    errors = []

    # Group sources by brand for logging
    brands_seen = {}
    for src in brand_sources:
        brands_seen.setdefault(src["brand_name"], []).append(src)

    logger.info(f"브랜드 소스 배치: {len(brands_seen)}개 브랜드, {len(brand_sources)}개 소스")
    for brand_name, sources in brands_seen.items():
        logger.info(f"  [{brand_name}] {len(sources)}개 소스: {[s['platform']+':'+s['source_value'] for s in sources]}")

    for idx, src in enumerate(brand_sources):
        label = f"{src['brand_name']}:{src['platform']}:{src['source_value']}"
        logger.info(f"=== [{idx + 1}/{len(brand_sources)}] 소스: {label} ===")

        try:
            result = scrape_source(src, mode=mode)
            domain_results[label] = result.model_dump(mode="json")
            total_scraped += result.ads_scraped
            total_new += result.ads_new
            total_updated += result.ads_updated
        except Exception as e:
            error_msg = f"[{label}] {type(e).__name__}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            log_activity(
                event_type="collection",
                event_subtype="batch_failed",
                title=f"Scrape failed: {label}",
                message=str(e),
            )
            domain_results[label] = BrandSourceScrapeResult(
                source_id=src["source_id"],
                platform=src["platform"],
                source_type=src["source_type"],
                source_value=src["source_value"],
                error=str(e),
            ).model_dump(mode="json")

        update_batch_run(
            run_id,
            total_ads_scraped=total_scraped,
            total_ads_new=total_new,
            total_ads_updated=total_updated,
            domain_results=domain_results,
            errors=errors,
        )

    return {
        "total_scraped": total_scraped,
        "total_new": total_new,
        "total_updated": total_updated,
        "domain_results": domain_results,
        "errors": errors,
    }


def _run_legacy_domains_batch(run_id: str, domains: list[MonitoredDomain], mode: str) -> dict:
    """Legacy monitored_domains 기반 배치 수집 실행."""
    total_scraped = 0
    total_new = 0
    total_updated = 0
    domain_results = {}
    errors = []

    for idx, d in enumerate(domains):
        logger.info(f"=== [{idx + 1}/{len(domains)}] 도메인: {d.domain} ===")

        try:
            if mode == "incremental":
                result = scrape_domain_incremental(d.domain)
            else:
                result = scrape_domain_fully(d.domain)
            domain_results[d.domain] = result.model_dump(mode="json")
            total_scraped += result.ads_scraped
            total_new += result.ads_new
            total_updated += result.ads_updated
        except Exception as e:
            error_msg = f"[{d.domain}] {type(e).__name__}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            log_activity(
                event_type="collection",
                event_subtype="batch_failed",
                title=f"Scrape failed: {d.domain}",
                message=str(e),
            )
            domain_results[d.domain] = DomainScrapeResult(
                domain=d.domain, error=str(e)
            ).model_dump(mode="json")

        update_batch_run(
            run_id,
            total_ads_scraped=total_scraped,
            total_ads_new=total_new,
            total_ads_updated=total_updated,
            domain_results=domain_results,
            errors=errors,
        )

    return {
        "total_scraped": total_scraped,
        "total_new": total_new,
        "total_updated": total_updated,
        "domain_results": domain_results,
        "errors": errors,
    }


def run_daily_batch(trigger_type: str = "manual", domain: str = "", dry_run: bool = False, mode: str = "full") -> dict:
    """메인 엔트리포인트:
    1. batch_run 레코드 생성
    2. brand_sources가 있으면 brand 기반 수집, 없으면 legacy monitored_domains 기반 수집
    3. 각 소스/도메인에 대해 스크래핑 실행
    4. 최종 update_batch_run()으로 status='completed', finished_at 기록
    5. 결과 summary dict 반환
    """
    # auto 모드: 일요일이면 full, 나머지 요일은 incremental
    if mode == "auto":
        if datetime.now().weekday() == 6:  # 일요일 = 6
            mode = "full"
            logger.info("auto 모드: 일요일 → full 수집")
        else:
            mode = "incremental"
            logger.info("auto 모드: 평일 → incremental 수집")

    # 단일 도메인 모드 (--domain flag): legacy path
    if domain:
        domains = [MonitoredDomain(domain=domain)]
        logger.info(f"단일 도메인 모드: {domain}")

        if dry_run:
            logger.info("DRY-RUN 모드: 스크래핑 없이 종료")
            return {
                "mode": "dry_run",
                "trigger_type": trigger_type,
                "total_domains": 1,
                "domains": [domain],
            }

        run_id = create_batch_run(trigger_type=trigger_type)
        update_batch_run(run_id, total_domains=1)
        batch_result = _run_legacy_domains_batch(run_id, domains, mode)
    else:
        # Try brand sources first, fall back to legacy domains
        brand_sources = get_active_brand_sources()

        if brand_sources:
            logger.info(f"브랜드 소스 모드: {len(brand_sources)}개 소스 (mode={mode})")
            total_items = len(brand_sources)

            if dry_run:
                logger.info("DRY-RUN 모드: 스크래핑 없이 종료")
                return {
                    "mode": "dry_run",
                    "trigger_type": trigger_type,
                    "total_sources": total_items,
                    "sources": [
                        f"{s['brand_name']}:{s['platform']}:{s['source_value']}"
                        for s in brand_sources
                    ],
                }

            run_id = create_batch_run(trigger_type=trigger_type)
            update_batch_run(run_id, total_domains=total_items)
            batch_result = _run_brand_sources_batch(run_id, brand_sources, mode)
        else:
            # Legacy: monitored_domains fallback
            domains = get_active_domains()
            logger.info(f"활성 도메인 {len(domains)}개 조회됨 (mode={mode}): {[d.domain for d in domains]}")
            total_items = len(domains)

            if dry_run:
                logger.info("DRY-RUN 모드: 스크래핑 없이 종료")
                return {
                    "mode": "dry_run",
                    "trigger_type": trigger_type,
                    "total_domains": total_items,
                    "domains": [d.domain for d in domains],
                }

            run_id = create_batch_run(trigger_type=trigger_type)
            update_batch_run(run_id, total_domains=total_items)
            batch_result = _run_legacy_domains_batch(run_id, domains, mode)

    total_scraped = batch_result["total_scraped"]
    total_new = batch_result["total_new"]
    total_updated = batch_result["total_updated"]
    domain_results = batch_result["domain_results"]
    errors = batch_result["errors"]

    # 최종 상태 업데이트
    final_status = BatchRunStatus.completed
    update_batch_run(
        run_id,
        status=final_status,
        finished_at=datetime.now(),
        total_ads_scraped=total_scraped,
        total_ads_new=total_new,
        total_ads_updated=total_updated,
        domain_results=domain_results,
        errors=errors,
    )

    log_activity(
        event_type="collection",
        event_subtype="batch_completed",
        title=f"Batch completed: {total_new} new, {total_updated} updated",
        metadata={
            "batch_run_id": run_id,
            "total_scraped": total_scraped,
            "total_new": total_new,
            "total_updated": total_updated,
            "errors_count": len(errors),
        },
    )

    summary = {
        "batch_run_id": run_id,
        "trigger_type": trigger_type,
        "mode": mode,
        "status": final_status.value,
        "total_sources": len(domain_results),
        "total_ads_scraped": total_scraped,
        "total_ads_new": total_new,
        "total_ads_updated": total_updated,
        "domain_results": domain_results,
        "errors": errors,
        "started_at": datetime.now().isoformat(),
    }

    logger.info(
        f"배치 완료: sources={len(domain_results)}, "
        f"scraped={total_scraped}, new={total_new}, updated={total_updated}, "
        f"errors={len(errors)}"
    )
    return summary


def main(trigger_type: str = "manual", domain: str = "", dry_run: bool = False, mode: str = "full") -> dict:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    return run_daily_batch(trigger_type=trigger_type, domain=domain, dry_run=dry_run, mode=mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily batch collector - monitored domains scraper")
    parser.add_argument("--domain", type=str, default="", help="Single domain to scrape (skip DB domain list)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="List domains only, no scraping")
    parser.add_argument("--trigger-type", type=str, default="manual", help="Trigger type (manual/scheduled)")
    parser.add_argument("--mode", choices=["full", "incremental", "auto"], default="full", help="Scraping mode (full/incremental/auto)")
    args = parser.parse_args()

    result = main(
        trigger_type=args.trigger_type,
        domain=args.domain,
        dry_run=args.dry_run,
        mode=args.mode,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"batch_collector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
