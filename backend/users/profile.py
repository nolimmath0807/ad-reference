import argparse
import json
from datetime import datetime
from pathlib import Path

from conn import get_db
from users.model import User


def get_profile(user_id: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, email, name, company, job_title, avatar_url, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        return {"error": {"code": "NOT_FOUND", "message": "사용자를 찾을 수 없습니다.", "details": None}}

    user = User(
        id=str(row[0]),
        email=row[1],
        name=row[2],
        company=row[3],
        job_title=row[4],
        avatar_url=row[5],
        created_at=row[6],
        updated_at=row[7],
    )
    return user.model_dump(mode="json")


def main(user_id: str) -> dict:
    return get_profile(user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get user profile")
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
