import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


def main() -> dict:
    user = User(
        id="550e8400-e29b-41d4-a716-446655440000",
        email="user@example.com",
        name="Hong Gildong",
        company="Funnel Crew",
        job_title="Performance Marketer",
        created_at=datetime(2026, 1, 15, 9, 0, 0),
        updated_at=datetime(2026, 2, 20, 14, 30, 0),
    )

    update_req = UserUpdateRequest(
        name="Kim Marketer",
        company="Funnel Crew",
        job_title="Performance Marketer",
    )

    return {
        "User": user.model_dump(mode="json"),
        "UserUpdateRequest": update_req.model_dump(mode="json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"users_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
