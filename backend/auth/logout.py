import argparse
import json
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from conn import get_db
from utils.auth_helper import verify_token


def logout(refresh_token: str) -> dict:
    payload = verify_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "유효하지 않은 리프레시 토큰입니다.",
                "details": None,
            }
        })

    with get_db() as (conn, cur):
        cur.execute(
            "INSERT INTO token_blacklist (token) VALUES (%s) ON CONFLICT DO NOTHING",
            (refresh_token,),
        )

    return {"message": "로그아웃되었습니다."}


def main(token: str) -> dict:
    return logout(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Logout user")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    result = main(args.token)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"logout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
