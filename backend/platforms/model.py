import argparse
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class PlatformType(str, Enum):
    meta = "meta"
    google = "google"
    tiktok = "tiktok"
    instagram = "instagram"


class Status(str, Enum):
    active = "active"
    limited = "limited"
    unavailable = "unavailable"


class PlatformStatus(BaseModel):
    platform: PlatformType
    status: Status
    message: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class PlatformAd(BaseModel):
    source_id: str
    platform: PlatformType
    format: str
    advertiser_name: str
    advertiser_handle: Optional[str] = None
    thumbnail_url: str
    preview_url: Optional[str] = None
    media_type: str
    ad_copy: Optional[str] = None
    cta_text: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tags: list[str] = []
    landing_page_url: Optional[str] = None
    raw_data: dict = {}


def main() -> dict:
    status = PlatformStatus(
        platform=PlatformType.meta,
        status=Status.active,
        message="Meta Ad Library API connected",
        last_synced_at=datetime(2026, 2, 23, 6, 0, 0),
    )

    platform_ad = PlatformAd(
        source_id="meta_12345",
        platform=PlatformType.meta,
        format="image",
        advertiser_name="Nike Korea",
        advertiser_handle="@nikekorea",
        thumbnail_url="https://example.com/thumb.jpg",
        media_type="image",
        ad_copy="Just Do It",
        tags=["ecommerce", "sports"],
        raw_data={"original_field": "value"},
    )

    return {
        "PlatformStatus": status.model_dump(mode="json"),
        "PlatformAd": platform_ad.model_dump(mode="json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Platform Pydantic models")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"platforms_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
