import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel

from ads.model import Ad


class FeaturedReferenceCreate(BaseModel):
    ad_id: str
    memo: Optional[str] = None


class FeaturedReference(BaseModel):
    id: str
    ad_id: str
    added_by: Optional[str] = None
    added_at: datetime
    memo: Optional[str] = None


class Curator(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    added_at: datetime


class FeaturedReferenceWithAd(BaseModel):
    ad_id: str
    first_added_at: datetime
    curators: list[Curator]
    ad: Ad


class FeaturedReferenceListResponse(BaseModel):
    items: list[FeaturedReferenceWithAd]
    total: int
    page: int
    limit: int
    has_next: bool


def main() -> dict:
    from ads.model import Format, MediaType, Platform

    ad = Ad(
        id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        platform=Platform.meta,
        format=Format.image,
        advertiser_name="Nike Korea",
        advertiser_handle="@nikekorea",
        thumbnail_url="https://example.com/thumb.jpg",
        media_type=MediaType.image,
        ad_copy="Just Do It",
        tags=["ecommerce", "sports"],
        created_at=datetime(2026, 2, 20, 10, 0, 0),
    )

    create_req = FeaturedReferenceCreate(
        ad_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        memo="Great example of brand storytelling",
    )

    featured_ref = FeaturedReference(
        id="f1e2d3c4-b5a6-7890-fedc-ba9876543210",
        ad_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        added_by="u1s2e3r4-a5b6-7890-user-ab1234567890",
        added_at=datetime(2026, 3, 1, 9, 0, 0),
        memo="Great example of brand storytelling",
    )

    curator = Curator(
        id="u1s2e3r4-a5b6-7890-user-ab1234567890",
        name="Admin User",
        avatar_url="https://example.com/avatar.jpg",
        added_at=datetime(2026, 3, 1, 9, 0, 0),
    )

    featured_with_ad = FeaturedReferenceWithAd(
        ad_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        first_added_at=datetime(2026, 3, 1, 9, 0, 0),
        curators=[curator],
        ad=ad,
    )

    list_resp = FeaturedReferenceListResponse(
        items=[featured_with_ad],
        total=1,
        page=1,
        limit=12,
        has_next=False,
    )

    return {
        "FeaturedReferenceCreate": create_req.model_dump(mode="json"),
        "FeaturedReference": featured_ref.model_dump(mode="json"),
        "FeaturedReferenceWithAd": featured_with_ad.model_dump(mode="json"),
        "FeaturedReferenceListResponse": list_resp.model_dump(mode="json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FeaturedReference Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"featured_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
