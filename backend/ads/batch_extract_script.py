"""광고 영상 원고 배치 추출 CLI.

Usage:
    cd backend && uv run ads/batch_extract_script.py --dry-run
    cd backend && uv run ads/batch_extract_script.py --limit 100
    cd backend && uv run ads/batch_extract_script.py --limit 50 --concurrency 3
    cd backend && uv run ads/batch_extract_script.py --retry-failed --limit 50
"""
import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from conn import get_db
from ads.extract_script import extract_script

logger = logging.getLogger("batch_extract_script")


def main(limit: int = 100, dry_run: bool = False, concurrency: int = 1, retry_failed: bool = False) -> dict:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 1. 대상 광고 ID 조회
    with get_db() as (conn, cur):
        if retry_failed:
            cur.execute(
                """
                SELECT a.id FROM ads a
                JOIN ad_scripts s ON a.id = s.ad_id
                WHERE a.media_type = 'video'
                  AND a.preview_url IS NOT NULL
                  AND s.status = 'failed'
                ORDER BY a.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT a.id FROM ads a
                LEFT JOIN ad_scripts s ON a.id = s.ad_id
                WHERE a.media_type = 'video'
                  AND a.preview_url IS NOT NULL
                  AND (s.ad_id IS NULL OR s.status = 'failed')
                ORDER BY a.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        ad_ids = [str(row[0]) for row in cur.fetchall()]

    total = len(ad_ids)
    logger.info(f"원고 추출 대상: {total}건 (limit={limit}, dry_run={dry_run}, concurrency={concurrency}, retry_failed={retry_failed})")

    if dry_run:
        logger.info("Dry run 모드 - 실제 처리하지 않음")
        return {"total": total, "dry_run": True}

    succeeded = 0
    failed = 0

    if concurrency <= 1:
        # 순차 처리
        for i, ad_id in enumerate(ad_ids, 1):
            result = extract_script(ad_id)
            if result.get("status") == "completed":
                succeeded += 1
            else:
                failed += 1
            logger.info(f"[{i}/{total}] {ad_id}: {result.get('status')}")

            if i < total:
                time.sleep(1.0)
    else:
        # 병렬 처리 (최대 3 권장)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_id = {executor.submit(extract_script, ad_id): ad_id for ad_id in ad_ids}
            completed = 0
            for future in as_completed(future_to_id):
                ad_id = future_to_id[future]
                completed += 1
                result = future.result()
                if result.get("status") == "completed":
                    succeeded += 1
                else:
                    failed += 1
                logger.info(f"[{completed}/{total}] {ad_id}: {result.get('status')}")

    logger.info(f"완료: succeeded={succeeded}, failed={failed}, total={total}")
    return {"total": total, "succeeded": succeeded, "failed": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch extract scripts from video ads"
    )
    parser.add_argument("--limit", type=int, default=100, help="Maximum ads to process")
    parser.add_argument("--dry-run", action="store_true", help="Show target count without processing")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of parallel workers (max 3 recommended)")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed status ads")
    args = parser.parse_args()

    result = main(args.limit, args.dry_run, args.concurrency, args.retry_failed)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"batch_extract_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
