import argparse
import json
from datetime import datetime
from pathlib import Path

import jwt as pyjwt
from fastapi import HTTPException

from auth.model import TokenResponse
from conn import get_db
from utils.auth_helper import (
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_EXPIRE_MINUTES,
)


def refresh_tokens(refresh_token: str) -> dict:
    # 1. verify refresh token
    try:
        payload = verify_token(refresh_token)
    except pyjwt.exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "REFRESH_TOKEN_EXPIRED",
                "message": "리프레시 토큰이 만료되었습니다. 다시 로그인해주세요.",
                "details": None,
            }
        })
    except pyjwt.exceptions.InvalidTokenError:
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "유효하지 않은 리프레시 토큰입니다.",
                "details": None,
            }
        })

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "유효하지 않은 리프레시 토큰입니다.",
                "details": None,
            }
        })

    # 2. check blacklist
    with get_db() as (conn, cur):
        cur.execute("SELECT 1 FROM token_blacklist WHERE token = %s", (refresh_token,))
        if cur.fetchone():
            raise HTTPException(status_code=401, detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "이미 무효화된 토큰입니다.",
                    "details": None,
                }
            })

    # 3. get user info from DB (to include email in new access token)
    user_id = payload["sub"]
    with get_db() as (conn, cur):
        cur.execute("SELECT email FROM users WHERE id = %s::uuid", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "사용자를 찾을 수 없습니다.",
                    "details": None,
                }
            })
        email = row[0]

    # 4. issue new tokens
    new_access = create_access_token(user_id, email)
    new_refresh = create_refresh_token(user_id)

    # 5. blacklist old refresh token (rotation)
    with get_db() as (conn, cur):
        cur.execute(
            "INSERT INTO token_blacklist (token) VALUES (%s) ON CONFLICT DO NOTHING",
            (refresh_token,),
        )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="Bearer",
        expires_in=ACCESS_EXPIRE_MINUTES * 60,
    ).model_dump()


def main(token: str) -> dict:
    return refresh_tokens(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh tokens")
    parser.add_argument("--token", required=True, help="Refresh token")
    args = parser.parse_args()

    result = main(args.token)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
