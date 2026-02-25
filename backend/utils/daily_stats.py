import logging

from conn import get_db

logger = logging.getLogger("daily_stats")


def record_daily_stats(
    brand_id: str,
    platform: str,
    new_count: int = 0,
    updated_count: int = 0,
    total_scraped: int = 0,
) -> None:
    """Record daily brand collection stats. UPSERT to accumulate same-day entries."""
    try:
        with get_db() as (conn, cur):
            cur.execute(
                """
                INSERT INTO daily_brand_stats (brand_id, platform, new_count, updated_count, total_scraped)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (brand_id, stat_date, platform) DO UPDATE SET
                    new_count = daily_brand_stats.new_count + EXCLUDED.new_count,
                    updated_count = daily_brand_stats.updated_count + EXCLUDED.updated_count,
                    total_scraped = daily_brand_stats.total_scraped + EXCLUDED.total_scraped,
                    updated_at = NOW()
                """,
                (brand_id, platform, new_count, updated_count, total_scraped),
            )
    except Exception as e:
        logger.warning(f"Failed to record daily stats: {e}")
