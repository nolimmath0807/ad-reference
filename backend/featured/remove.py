import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db


def remove_featured(ad_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "DELETE FROM featured_references WHERE ad_id = %s::uuid RETURNING id",
            (ad_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "추천 레퍼런스를 찾을 수 없습니다.",
                    "details": None,
                }
            })
    return {"success": True}


def main(ad_id: str) -> dict:
    return remove_featured(ad_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove a featured reference")
    parser.add_argument("--ad-id", required=True)
    args = parser.parse_args()

    result = main(args.ad_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"remove_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
