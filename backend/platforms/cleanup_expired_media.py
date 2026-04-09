import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import httpx
from conn import get_db

logger = logging.getLogger("cleanup_expired_media")

NON_EXPIRED_PATTERNS = ("%s3.%", "%amazonaws%", "/static/%")


def find_cdn_ads(cur, max_check: int) -> list[dict]:
    cur.execute(
        """
        SELECT id, thumbnail_url, preview_url, platform, advertiser_name
        FROM ads
        WHERE thumbnail_url IS NOT NULL
          AND thumbnail_url != ''
          AND thumbnail_url NOT LIKE %s
          AND thumbnail_url NOT LIKE %s
          AND thumbnail_url NOT LIKE %s
        LIMIT %s
        """,
        (*NON_EXPIRED_PATTERNS, max_check),
    )
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def check_url(client: httpx.Client, url: str) -> bool:
    resp = client.head(url, follow_redirects=True, timeout=5.0)
    return resp.status_code == 200


def check_ads(ads: list[dict], batch_size: int) -> tuple[list[dict], list[dict]]:
    alive = []
    expired = []

    with httpx.Client() as client:
        for i, ad in enumerate(ads):
            url = ad["thumbnail_url"]
            try:
                is_alive = check_url(client, url)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError):
                is_alive = False

            if is_alive:
                alive.append(ad)
            else:
                expired.append(ad)

            if (i + 1) % batch_size == 0:
                logger.info(f"Checked {i + 1}/{len(ads)} ...")

            time.sleep(0.1)

    return alive, expired


def delete_ads(cur, ad_ids: list[int]) -> int:
    cur.execute("DELETE FROM ads WHERE id = ANY(%s)", (ad_ids,))
    return cur.rowcount


def main(dry_run: bool, execute: bool, batch_size: int, max_check: int) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with get_db() as (conn, cur):
        ads = find_cdn_ads(cur, max_check)
        logger.info(f"CDN URL ads found: {len(ads)}")

        if not ads:
            logger.info("No CDN URL ads to check.")
            return {"total": 0, "alive": 0, "expired": 0, "deleted": 0}

        alive, expired = check_ads(ads, batch_size)

        logger.info("")
        logger.info(f"Total checked: {len(ads)}")
        logger.info(f"Alive (keep):  {len(alive)}")
        logger.info(f"Expired:       {len(expired)}")
        logger.info("---")

        deleted = 0
        if expired:
            for ad in expired[:20]:
                logger.info(f"  EXPIRED: [{ad['platform']}] {ad['advertiser_name']} - {ad['thumbnail_url'][:80]}")
            if len(expired) > 20:
                logger.info(f"  ... and {len(expired) - 20} more")

        if execute and not dry_run:
            expired_ids = [ad["id"] for ad in expired]
            deleted = delete_ads(cur, expired_ids)
            logger.info(f"Deleted {deleted} ads from DB.")
        else:
            logger.info("DRY-RUN mode: no deletion. Use --execute to delete.")

    return {
        "total": len(ads),
        "alive": len(alive),
        "expired": len(expired),
        "deleted": deleted,
        "expired_ads": [
            {"id": ad["id"], "platform": ad["platform"], "advertiser_name": ad["advertiser_name"]}
            for ad in expired
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup ads with expired CDN media URLs")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Show targets without deleting (default)")
    parser.add_argument("--execute", action="store_true", help="Actually delete expired ads")
    parser.add_argument("--batch-size", type=int, default=50, help="Log progress every N checks (default: 50)")
    parser.add_argument("--max-check", type=int, default=1000, help="Max ads to check (default: 1000)")
    args = parser.parse_args()

    result = main(
        dry_run=args.dry_run,
        execute=args.execute,
        batch_size=args.batch_size,
        max_check=args.max_check,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"cleanup_expired_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
