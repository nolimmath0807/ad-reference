import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from platforms.model import PlatformAd


async def search_meta_ads(
    keyword: str,
    country: str = "KR",
    ad_type: str = "ALL",
    limit: int = 25,
) -> list[PlatformAd]:
    from platforms.meta_scraper import scrape_meta_ads as _scrape
    return await asyncio.to_thread(_scrape, keyword, headless=True, max_results=limit)


async def get_meta_ad_detail(ad_id: str) -> PlatformAd | None:
    return None


def main(keyword: str, limit: int = 25) -> dict:
    ads = asyncio.run(search_meta_ads(keyword, limit=limit))
    return {
        "platform": "meta",
        "keyword": keyword,
        "count": len(ads),
        "ads": [ad.model_dump(mode="json") for ad in ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta Ad Library Scraper Wrapper")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of results")
    args = parser.parse_args()

    result = main(args.keyword, limit=args.limit)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"meta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
