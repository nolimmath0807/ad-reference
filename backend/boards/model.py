import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel

from ads.model import Ad


class Board(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    item_count: int
    created_at: datetime
    updated_at: datetime


class BoardCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class BoardItem(BaseModel):
    id: str
    board_id: str
    ad_id: str
    ad: Ad
    added_at: datetime


class BoardItemAddRequest(BaseModel):
    ad_id: str


class BoardListResponse(BaseModel):
    items: list[Board]
    total: int
    page: int
    limit: int
    has_next: bool


class BoardDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    item_count: int
    created_at: datetime
    updated_at: datetime
    items: list[BoardItem]
    total: int
    page: int
    limit: int
    has_next: bool


def main() -> dict:
    board = Board(
        id="b1c2d3e4-f5a6-7890-bcde-f12345678901",
        name="Competitor Analysis",
        description="Main competitor ads",
        item_count=12,
        created_at=datetime(2026, 2, 1, 10, 0, 0),
        updated_at=datetime(2026, 2, 20, 14, 30, 0),
    )

    create_req = BoardCreateRequest(name="Creative References", description="Marketing team refs")

    add_req = BoardItemAddRequest(ad_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    list_resp = BoardListResponse(
        items=[board],
        total=1,
        page=1,
        limit=12,
        has_next=False,
    )

    return {
        "Board": board.model_dump(mode="json"),
        "BoardCreateRequest": create_req.model_dump(mode="json"),
        "BoardItemAddRequest": add_req.model_dump(mode="json"),
        "BoardListResponse": list_resp.model_dump(mode="json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Board Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"boards_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
