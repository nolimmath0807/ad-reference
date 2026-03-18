import argparse
import json
import secrets
import string
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db
from utils.auth_helper import hash_password


def reset_user_password(user_id: str) -> dict:
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    hashed = hash_password(temp_password)

    with get_db() as (conn, cur):
        cur.execute(
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s::uuid RETURNING id, email",
            (hashed, user_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "USER_NOT_FOUND", "message": "사용자를 찾을 수 없습니다.", "details": None}},
            )

    return {"user_id": str(row[0]), "email": row[1], "temp_password": temp_password}


def main(user_id: str) -> dict:
    return reset_user_password(user_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset user password (admin)")
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()

    result = main(args.user_id)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"reset_password_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
