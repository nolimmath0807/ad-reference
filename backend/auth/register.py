import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from auth.model import RegisterRequest, TokenResponse
from conn import get_db
from utils.auth_helper import (
    create_access_token,
    create_refresh_token,
    hash_password,
    ACCESS_EXPIRE_MINUTES,
)
from utils.validation import validate_email, validate_password


def register(request: RegisterRequest) -> dict:
    if not validate_email(request.email):
        raise HTTPException(status_code=400, detail={
            "error": {
                "code": "BAD_REQUEST",
                "message": "올바른 이메일 형식이 아닙니다.",
                "details": [{"field": "email", "message": "올바른 이메일 형식이 아닙니다."}],
            }
        })

    if not validate_password(request.password):
        raise HTTPException(status_code=400, detail={
            "error": {
                "code": "BAD_REQUEST",
                "message": "비밀번호는 8자 이상이며 숫자를 포함해야 합니다.",
                "details": [{"field": "password", "message": "비밀번호는 8자 이상이며 숫자를 포함해야 합니다."}],
            }
        })

    password_hash = hash_password(request.password)

    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "이미 등록된 이메일입니다.",
                    "details": None,
                }
            })

        cur.execute(
            """
            INSERT INTO users (email, password_hash, name)
            VALUES (%s, %s, %s)
            RETURNING id, email, name, company, job_title, avatar_url, created_at, updated_at
            """,
            (request.email, password_hash, request.name),
        )
        row = cur.fetchone()

    user_id = str(row[0])
    access_token = create_access_token(user_id, row[1])
    refresh_token = create_refresh_token(user_id)

    user = {
        "id": user_id,
        "email": row[1],
        "name": row[2],
        "company": row[3],
        "job_title": row[4],
        "avatar_url": row[5],
        "created_at": row[6].isoformat(),
        "updated_at": row[7].isoformat(),
    }

    tokens = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_EXPIRE_MINUTES * 60,
    ).model_dump()

    return {"user": user, "tokens": tokens}


def main(email: str, password: str, name: str) -> dict:
    request = RegisterRequest(email=email, password=password, name=name)
    return register(request)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register a new user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    result = main(args.email, args.password, args.name)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"register_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
