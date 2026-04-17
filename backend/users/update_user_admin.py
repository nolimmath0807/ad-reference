import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from conn import get_db
from utils.serialize import serialize_row


def update_user_admin(user_id: str, is_approved: Optional[bool] = None, role: Optional[str] = None) -> dict:
    if role is not None and role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail={
            "error": {
                "code": "BAD_REQUEST",
                "message": "role은 'admin' 또는 'user'만 허용됩니다.",
                "details": None,
            }
        })

    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM users WHERE id = %s::uuid", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "유저를 찾을 수 없습니다.",
                    "details": None,
                }
            })

        updates = []
        params = []
        if is_approved is not None:
            updates.append("is_approved = %s")
            params.append(is_approved)
        if role is not None:
            updates.append("role = %s")
            params.append(role)

        if not updates:
            raise HTTPException(status_code=400, detail={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "변경할 항목이 없습니다.",
                    "details": None,
                }
            })

        updates.append("updated_at = NOW()")
        params.append(user_id)

        cur.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s::uuid "
            "RETURNING id, email, name, company, job_title, role, is_approved, created_at, updated_at",
            params,
        )
        row = cur.fetchone()

    cols = ["id", "email", "name", "company", "job_title", "role", "is_approved", "created_at", "updated_at"]
    return serialize_row(cols, row)


def main(user_id: str, is_approved: Optional[bool] = None, role: Optional[str] = None) -> dict:
    return update_user_admin(user_id, is_approved=is_approved, role=role)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin update user (approve/role)")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--is-approved", type=lambda v: v.lower() == "true", default=None)
    parser.add_argument("--role", default=None)
    args = parser.parse_args()

    result = main(args.user_id, is_approved=args.is_approved, role=args.role)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"update_user_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
