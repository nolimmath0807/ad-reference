import argparse
import json
from datetime import datetime
from pathlib import Path

from conn import get_db
from users.model import User
from utils.auth_helper import hash_password, verify_password
from utils.validation import validate_password


def update_profile(
    user_id: str,
    name: str | None = None,
    company: str | None = None,
    job_title: str | None = None,
    current_password: str | None = None,
    new_password: str | None = None,
) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, email, name, company, job_title, avatar_url, password_hash, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

        if not row:
            return {"error": {"code": "NOT_FOUND", "message": "사용자를 찾을 수 없습니다.", "details": None}}

        current_name = row[2]
        current_company = row[3]
        current_job_title = row[4]
        stored_hash = row[6]

        updates = {}
        if name is not None:
            updates["name"] = name
        if company is not None:
            updates["company"] = company
        if job_title is not None:
            updates["job_title"] = job_title

        if current_password and new_password:
            if not verify_password(current_password, stored_hash):
                return {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "현재 비밀번호가 일치하지 않습니다.",
                        "details": [{"field": "current_password", "message": "현재 비밀번호가 일치하지 않습니다."}],
                    }
                }
            if not validate_password(new_password):
                return {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "새 비밀번호는 8자 이상이며 숫자를 포함해야 합니다.",
                        "details": [{"field": "new_password", "message": "새 비밀번호는 8자 이상이며 숫자를 포함해야 합니다."}],
                    }
                }
            updates["password_hash"] = hash_password(new_password)

        if not updates:
            user = User(
                id=str(row[0]),
                email=row[1],
                name=current_name,
                company=current_company,
                job_title=current_job_title,
                avatar_url=row[5],
                created_at=row[7],
                updated_at=row[8],
            )
            return user.model_dump(mode="json")

        set_clauses = [f"{col} = %s" for col in updates]
        set_clauses.append("updated_at = NOW()")
        values = list(updates.values())
        values.append(user_id)

        cur.execute(
            f"""
            UPDATE users
            SET {', '.join(set_clauses)}
            WHERE id = %s
            RETURNING id, email, name, company, job_title, avatar_url, created_at, updated_at
            """,
            values,
        )
        updated_row = cur.fetchone()

    user = User(
        id=str(updated_row[0]),
        email=updated_row[1],
        name=updated_row[2],
        company=updated_row[3],
        job_title=updated_row[4],
        avatar_url=updated_row[5],
        created_at=updated_row[6],
        updated_at=updated_row[7],
    )
    return user.model_dump(mode="json")


def main(
    user_id: str,
    name: str | None = None,
    company: str | None = None,
    job_title: str | None = None,
    current_password: str | None = None,
    new_password: str | None = None,
) -> dict:
    return update_profile(user_id, name, company, job_title, current_password, new_password)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update user profile")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--name")
    parser.add_argument("--company")
    parser.add_argument("--job-title")
    parser.add_argument("--current-password")
    parser.add_argument("--new-password")
    args = parser.parse_args()

    result = main(
        args.user_id,
        name=args.name,
        company=args.company,
        job_title=args.job_title,
        current_password=args.current_password,
        new_password=args.new_password,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
