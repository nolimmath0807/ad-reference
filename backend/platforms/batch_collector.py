import argparse
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from conn import get_db
from platforms.google_scraper import scrape_google_ads_by_domain
from platforms.model import BatchRunStatus, DomainScrapeResult, MonitoredDomain
from platforms.scrape_worker import upsert_ads_batch

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


def run_daily_batch(trigger_type: str = "manual", domain: str = "", dry_run: bool = False, mode: str = "full") -> dict:
    """메인 엔트리포인트:
    1. batch_run 레코드 생성
    2. get_active_domains()로 도메인 목록 조회
    3. 각 도메인에 대해 scrape_domain_fully() 실행
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

    # 도메인 목록 결정
    if domain:
        domains = [MonitoredDomain(domain=domain)]
        logger.info(f"단일 도메인 모드: {domain}")
    else:
        domains = get_active_domains()
        logger.info(f"활성 도메인 {len(domains)}개 조회됨 (mode={mode}): {[d.domain for d in domains]}")

    # dry-run 모드: 도메인 목록만 출력 후 종료
    if dry_run:
        logger.info("DRY-RUN 모드: 스크래핑 없이 종료")
        return {
            "mode": "dry_run",
            "trigger_type": trigger_type,
            "total_domains": len(domains),
            "domains": [d.domain for d in domains],
        }

    # batch_run 레코드 생성
    run_id = create_batch_run(trigger_type=trigger_type)
    update_batch_run(run_id, total_domains=len(domains))

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
            domain_results[d.domain] = DomainScrapeResult(
                domain=d.domain, error=str(e)
            ).model_dump(mode="json")

        # 매 도메인 완료 시 중간 결과 저장
        update_batch_run(
            run_id,
            total_ads_scraped=total_scraped,
            total_ads_new=total_new,
            total_ads_updated=total_updated,
            domain_results=domain_results,
            errors=errors,
        )

    # 최종 상태 업데이트
    final_status = BatchRunStatus.completed if not errors else BatchRunStatus.completed
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

    summary = {
        "batch_run_id": run_id,
        "trigger_type": trigger_type,
        "mode": mode,
        "status": final_status.value,
        "total_domains": len(domains),
        "total_ads_scraped": total_scraped,
        "total_ads_new": total_new,
        "total_ads_updated": total_updated,
        "domain_results": domain_results,
        "errors": errors,
        "started_at": datetime.now().isoformat(),
    }

    logger.info(
        f"배치 완료: domains={len(domains)}, "
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
