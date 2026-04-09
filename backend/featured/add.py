import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def add_featured(ad_id: str, added_by: str, memo: str | None = None) -> dict:
    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM ads WHERE id = %s::uuid", (ad_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "광고를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        cur.execute("SELECT id FROM featured_references WHERE ad_id = %s::uuid AND added_by = %s::uuid", (ad_id, added_by))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "이미 추천 목록에 등록된 광고입니다.",
                    "details": None,
                }
            })

        cur.execute(
            "INSERT INTO featured_references (ad_id, added_by, memo) VALUES (%s::uuid, %s::uuid, %s) RETURNING id, ad_id, added_by, added_at, memo",
            (ad_id, added_by, memo),
        )
        row = cur.fetchone()

    return {
        "id": str(row[0]),
        "ad_id": str(row[1]),
        "added_by": str(row[2]) if row[2] else None,
        "added_at": row[3].isoformat(),
        "memo": row[4],
    }


def main(ad_id: str, added_by: str, memo: str | None = None) -> dict:
    return add_featured(ad_id, added_by, memo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add an ad to featured references")
    parser.add_argument("--ad-id", required=True)
    parser.add_argument("--added-by", required=True)
    parser.add_argument("--memo", required=False, default=None)
    args = parser.parse_args()

    result = main(args.ad_id, args.added_by, args.memo)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"add_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
