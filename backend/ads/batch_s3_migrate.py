"""YouTube URL로 저장된 preview_url을 S3로 마이그레이션하는 배치 CLI.

Usage:
    cd backend && uv run ads/batch_s3_migrate.py --dry-run
    cd backend && uv run ads/batch_s3_migrate.py --limit 50
    cd backend && uv run ads/batch_s3_migrate.py --limit 100 --concurrency 3
"""
import argparse
import json
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from conn import get_db
from ads.extract_script import _download_youtube
from platforms.s3 import upload_from_file

logger = logging.getLogger("batch_s3_migrate")


def migrate_one(ad_id: str, preview_url: str) -> bool:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        _download_youtube(preview_url, tmp_path)

        s3_key = f"videos/{ad_id}.mp4"
        s3_url = upload_from_file(tmp_path, s3_key)

        if s3_url:
            with get_db() as (conn, cur):
                cur.execute(
                    "UPDATE ads SET preview_url = %s WHERE id = %s",
                    (s3_url, ad_id),
                )
            logger.info(f"{ad_id}: migrated -> {s3_url}")
            return True

        logger.warning(f"{ad_id}: S3 업로드 실패 (upload_from_file returned None)")
        return False

    except Exception as e:
        logger.error(f"{ad_id}: ERROR - {e}")
        return False

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main(limit: int, dry_run: bool, concurrency: int) -> dict:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 1. YouTube URL인 video 광고 조회
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, preview_url FROM ads
            WHERE media_type = 'video'
              AND (preview_url LIKE '%%youtube.com%%' OR preview_url LIKE '%%youtu.be%%')
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = [(str(row[0]), row[1]) for row in cur.fetchall()]

    total = len(rows)
    logger.info(f"마이그레이션 대상: {total}건 (limit={limit}, dry_run={dry_run}, concurrency={concurrency})")

    if dry_run:
        logger.info("Dry run 모드 - 실제 처리하지 않음")
        return {"total": total, "dry_run": True}

    succeeded = 0
    failed = 0

    if concurrency <= 1:
        # 순차 처리
        for i, (ad_id, preview_url) in enumerate(rows, 1):
            result = migrate_one(ad_id, preview_url)
            if result:
                succeeded += 1
            else:
                failed += 1
            logger.info(f"[{i}/{total}] {ad_id}: {'OK' if result else 'FAIL'}")

            # yt-dlp YouTube rate limit 고려
            if i < total:
                time.sleep(2.0)

    else:
        # 병렬 처리 — 최대 3 권장 (YouTube rate limit 주의)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_id = {
                executor.submit(migrate_one, ad_id, preview_url): ad_id
                for ad_id, preview_url in rows
            }
            done_count = 0
            for future in as_completed(future_to_id):
                ad_id = future_to_id[future]
                done_count += 1
                result = future.result()
                if result:
                    succeeded += 1
                else:
                    failed += 1
                logger.info(f"[{done_count}/{total}] {ad_id}: {'OK' if result else 'FAIL'}")

    logger.info(f"완료: succeeded={succeeded}, failed={failed}, total={total}")
    return {"total": total, "succeeded": succeeded, "failed": failed, "dry_run": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube preview_url을 yt-dlp 다운로드 → S3 업로드 → DB 교체"
    )
    parser.add_argument("--limit", type=int, default=50, help="처리할 최대 건수 (기본 50)")
    parser.add_argument("--dry-run", action="store_true", help="대상 건수만 출력, 실제 처리 안 함")
    parser.add_argument("--concurrency", type=int, default=1, help="동시 처리 수 (기본 1, 최대 3 권장)")
    args = parser.parse_args()

    result = main(args.limit, args.dry_run, args.concurrency)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"batch_s3_migrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
