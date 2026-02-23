import argparse
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str


def main() -> dict:
    login = LoginRequest(email="user@example.com", password="secureP@ss123")
    register = RegisterRequest(email="new@example.com", password="secureP@ss123", name="Kim")
    token = TokenResponse(
        access_token="eyJ...",
        refresh_token="eyJ...",
        token_type="Bearer",
        expires_in=3600,
    )
    logout = LogoutRequest(refresh_token="eyJ...")

    return {
        "LoginRequest": login.model_dump(),
        "RegisterRequest": register.model_dump(),
        "TokenResponse": token.model_dump(),
        "LogoutRequest": logout.model_dump(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auth Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"auth_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
