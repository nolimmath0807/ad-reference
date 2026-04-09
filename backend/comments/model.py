import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str


class Comment(BaseModel):
    id: str
    ad_id: str
    user_id: str
    user_name: str
    user_avatar_url: Optional[str] = None
    content: str
    created_at: datetime


class CommentListResponse(BaseModel):
    items: list[Comment]
    total: int


def main() -> dict:
    c = Comment(
        id="c1d2e3f4-a5b6-7890-abcd-ef1234567890",
        ad_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        user_id="u1s2e3r4-a5b6-7890-user-ab1234567890",
        user_name="김진우",
        user_avatar_url=None,
        content="이 광고 훅이 정말 강력하네요",
        created_at=datetime(2026, 4, 9, 10, 0, 0),
    )
    resp = CommentListResponse(items=[c], total=1)
    return resp.model_dump(mode="json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comment models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"comment_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
