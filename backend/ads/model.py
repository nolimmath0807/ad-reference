import argparse
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Platform(str, Enum):
    meta = "meta"
    google = "google"
    tiktok = "tiktok"


class Format(str, Enum):
    image = "image"
    video = "video"
    carousel = "carousel"
    reels = "reels"
    text = "text"


class MediaType(str, Enum):
    image = "image"
    video = "video"
    text = "text"


class Ad(BaseModel):
    id: str
    platform: Platform
    format: Format
    advertiser_name: str
    advertiser_handle: Optional[str] = None
    advertiser_avatar_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    media_type: MediaType
    ad_copy: Optional[str] = None
    cta_text: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tags: list[str]
    landing_page_url: Optional[str] = None
    created_at: datetime
    saved_at: Optional[datetime] = None


class AdSearchResponse(BaseModel):
    items: list[Ad]
    total: int
    page: int
    limit: int
    has_next: bool


class AdDetailResponse(BaseModel):
    ad: Ad
    similar_ads: list[Ad]


class AdSaveRequest(BaseModel):
    platform: Platform
    format: Format
    advertiser_name: str
    advertiser_handle: Optional[str] = None
    advertiser_avatar_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    media_type: MediaType
    ad_copy: Optional[str] = None
    cta_text: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tags: list[str] = []
    landing_page_url: Optional[str] = None


def main() -> dict:
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

    search_resp = AdSearchResponse(
        items=[ad],
        total=1,
        page=1,
        limit=20,
        has_next=False,
    )

    detail_resp = AdDetailResponse(ad=ad, similar_ads=[])

    save_req = AdSaveRequest(
        platform=Platform.meta,
        format=Format.image,
        advertiser_name="Nike Korea",
        thumbnail_url="https://example.com/thumb.jpg",
        media_type=MediaType.image,
        tags=["ecommerce"],
    )

    return {
        "Ad": ad.model_dump(mode="json"),
        "AdSearchResponse": search_resp.model_dump(mode="json"),
        "AdDetailResponse": detail_resp.model_dump(mode="json"),
        "AdSaveRequest": save_req.model_dump(mode="json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ad Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"ads_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
