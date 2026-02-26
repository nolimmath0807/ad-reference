import argparse
import hashlib
import logging
from collections import defaultdict
from urllib.parse import urlparse

from conn import get_db

logger = logging.getLogger("dedup_meta")


def make_source_id(advertiser_name: str, content_url: str) -> str:
    parsed = urlparse(content_url)
    stable_url = parsed.path
    raw = f"meta:{advertiser_name}:{stable_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def main(dry_run: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    with get_db() as (conn, cur):
        # 1. 모든 Meta 광고 조회
        cur.execute("""
            SELECT id, advertiser_name, preview_url, thumbnail_url, created_at
            FROM ads
            WHERE platform = 'meta'
            ORDER BY created_at ASC
        """)
        rows = cur.fetchall()
        logger.info(f"Total meta ads: {len(rows)}")

        # 2. thumbnail URL path 기준으로 그룹화
        groups = defaultdict(list)
        for row in rows:
            ad_id, adv_name, preview_url, thumb_url, created_at = row
            # thumbnail path가 가장 안정적인 식별자
            if thumb_url:
                path = urlparse(thumb_url).path
            elif preview_url:
                path = urlparse(preview_url).path
            else:
                path = ""
            key = (adv_name, path)
            groups[key].append(row)

        # 3. 중복 그룹 찾기
        duplicates_to_delete = []
        ids_to_update = []

        for key, items in groups.items():
            if len(items) > 1:
                # 가장 오래된 것 유지 (이미 created_at ASC로 정렬됨)
                keep = items[0]
                delete_items = items[1:]
                duplicates_to_delete.extend([item[0] for item in delete_items])

                # 남길 광고의 source_id를 새 로직으로 업데이트
                adv_name = keep[1]
                preview_url = keep[2] or ""
                new_source_id = make_source_id(adv_name, preview_url)
                ids_to_update.append((new_source_id, keep[0]))

        dup_group_count = len([g for g in groups.values() if len(g) > 1])
        logger.info(f"Duplicate groups: {dup_group_count}")
        logger.info(f"Ads to delete: {len(duplicates_to_delete)}")
        logger.info(f"Ads to update source_id: {len(ids_to_update)}")

        if dry_run:
            logger.info("DRY RUN - no changes made")
            return

        # 4. 중복 삭제
        if duplicates_to_delete:
            # board_items 참조 확인 후 삭제
            cur.execute("DELETE FROM board_items WHERE ad_id = ANY(%s::uuid[])", (duplicates_to_delete,))
            deleted_board_items = cur.rowcount
            logger.info(f"Deleted {deleted_board_items} board_items referencing duplicates")

            cur.execute("DELETE FROM ads WHERE id = ANY(%s::uuid[])", (duplicates_to_delete,))
            logger.info(f"Deleted {cur.rowcount} duplicate ads")

        # 5. 남은 광고 source_id 업데이트
        extra_deleted = 0
        for new_source_id, ad_id in ids_to_update:
            # 새 source_id가 이미 존재하면, 이 광고도 삭제 (최신 버전이 이미 있음)
            cur.execute(
                "SELECT id FROM ads WHERE source_id = %s AND platform = 'meta' AND id != %s",
                (new_source_id, ad_id),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM board_items WHERE ad_id = %s", (ad_id,))
                cur.execute("DELETE FROM ads WHERE id = %s", (ad_id,))
                extra_deleted += 1
            else:
                cur.execute("UPDATE ads SET source_id = %s WHERE id = %s", (new_source_id, ad_id))
        logger.info(f"Updated source_ids: {len(ids_to_update) - extra_deleted}, extra deleted: {extra_deleted}")

    logger.info("Deduplication complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta ads deduplication")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
