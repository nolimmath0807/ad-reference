import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from auth.model import LoginRequest, TokenResponse
from conn import get_db
from utils.auth_helper import (
    create_access_token,
    create_refresh_token,
    verify_password,
    ACCESS_EXPIRE_MINUTES,
)


def login(request: LoginRequest) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, email, password_hash FROM users WHERE email = %s",
            (request.email,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "이메일 또는 비밀번호가 올바르지 않습니다.",
                "details": None,
            }
        })

    user_id = str(row[0])
    email = row[1]
    password_hash = row[2]

    if not verify_password(request.password, password_hash):
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "이메일 또는 비밀번호가 올바르지 않습니다.",
                "details": None,
            }
        })

    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_EXPIRE_MINUTES * 60,
    ).model_dump()


def main(email: str, password: str) -> dict:
    request = LoginRequest(email=email, password=password)
    return login(request)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Login user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    result = main(args.email, args.password)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
