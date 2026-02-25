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
    domain: str = ""
    raw_data: dict = {}
    creative_id: str | None = None
    brand_id: str | None = None


class MonitoredDomain(BaseModel):
    id: Optional[str] = None
    domain: str
    platform: PlatformType = PlatformType.google
    is_active: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BatchRunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class BatchRun(BaseModel):
    id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: BatchRunStatus = BatchRunStatus.running
    total_domains: int = 0
    total_ads_scraped: int = 0
    total_ads_new: int = 0
    total_ads_updated: int = 0
    domain_results: dict = {}
    errors: list = []
    trigger_type: str = "manual"


class DomainScrapeResult(BaseModel):
    domain: str
    ads_scraped: int = 0
    ads_new: int = 0
    ads_updated: int = 0
    duration_seconds: float = 0
    error: Optional[str] = None


class Brand(BaseModel):
    id: str | None = None
    brand_name: str
    is_active: bool = True
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BrandSource(BaseModel):
    id: str | None = None
    brand_id: str
    platform: str  # 'google' | 'meta' | 'tiktok'
    source_type: str  # 'domain' | 'keyword' | 'page_id'
    source_value: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BrandWithSources(BaseModel):
    """Brand with its sources list"""
    brand: Brand
    sources: list[BrandSource] = []


class BrandSourceScrapeResult(BaseModel):
    source_id: str
    platform: str
    source_type: str
    source_value: str
    ads_scraped: int = 0
    ads_new: int = 0
    ads_updated: int = 0
    duration_seconds: float = 0
    error: str | None = None


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

    monitored_domain = MonitoredDomain(
        domain="nike.com",
        platform=PlatformType.google,
        is_active=True,
        notes="Global brand tracking",
    )

    domain_result = DomainScrapeResult(
        domain="nike.com",
        ads_scraped=42,
        ads_new=10,
        ads_updated=32,
        duration_seconds=12.5,
    )

    batch_run = BatchRun(
        status=BatchRunStatus.completed,
        total_domains=3,
        total_ads_scraped=120,
        total_ads_new=25,
        total_ads_updated=95,
        domain_results={"nike.com": domain_result.model_dump(mode="json")},
        trigger_type="manual",
    )

    return {
        "PlatformStatus": status.model_dump(mode="json"),
        "PlatformAd": platform_ad.model_dump(mode="json"),
        "MonitoredDomain": monitored_domain.model_dump(mode="json"),
        "DomainScrapeResult": domain_result.model_dump(mode="json"),
        "BatchRun": batch_run.model_dump(mode="json"),
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
