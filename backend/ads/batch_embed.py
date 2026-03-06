"""기존 광고에 대한 CLIP 임베딩 배치 생성 CLI.

Usage:
    cd backend && uv run ads/batch_embed.py --limit 500
    cd backend && uv run ads/batch_embed.py --limit 50 --dry-run
"""
import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from conn import get_db
from ads.embedding import embed_ad

logger = logging.getLogger("batch_embed")


def main(limit: int = 100, dry_run: bool = False) -> dict:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 1. 임베딩이 없는 광고 ID 목록 조회
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT a.id FROM ads a
            LEFT JOIN ad_embeddings e ON a.id = e.ad_id AND e.status = 'completed'
            WHERE e.id IS NULL
            ORDER BY a.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        ad_ids = [str(row[0]) for row in cur.fetchall()]

    total = len(ad_ids)
    logger.info(f"임베딩 대상: {total}건 (limit={limit}, dry_run={dry_run})")

    if dry_run:
        logger.info("Dry run 모드 - 실제 처리하지 않음")
        return {"total": total, "dry_run": True}

    succeeded = 0
    failed = 0

    for i, ad_id in enumerate(ad_ids, 1):
        try:
            result = embed_ad(ad_id)
            if result.get("status") == "completed":
                succeeded += 1
            else:
                failed += 1
            logger.info(f"[{i}/{total}] {ad_id}: {result.get('status')}")
        except Exception as e:
            failed += 1
            logger.error(f"[{i}/{total}] {ad_id}: ERROR - {e}")

        # Rate limiting
        if i < total:
            time.sleep(1.0)

    logger.info(f"완료: succeeded={succeeded}, failed={failed}, total={total}")
    return {"total": total, "succeeded": succeeded, "failed": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch generate CLIP embeddings for ads"
    )
    parser.add_argument("--limit", type=int, default=100, help="Maximum ads to process")
    parser.add_argument("--dry-run", action="store_true", help="Show target count without processing")
    args = parser.parse_args()

    result = main(args.limit, args.dry_run)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"batch_embed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
