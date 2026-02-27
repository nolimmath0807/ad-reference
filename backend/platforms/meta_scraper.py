import argparse
import hashlib
import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

from platforms.model import PlatformAd, PlatformType

logger = logging.getLogger("meta_scraper")

try:
    from dateutil.relativedelta import relativedelta
    _THREE_MONTHS_AGO = date.today() - relativedelta(months=3)
except ImportError:
    _THREE_MONTHS_AGO = date.today() - timedelta(days=90)

BLOCKED_DOMAINS = [
    "naver.",
    "kakao.",
    "facebook.",
    "instagram.",
]


def is_blocked_url(url: str) -> bool:
    if not url:
        return False
    return any(domain in url.lower() for domain in BLOCKED_DOMAINS)


def make_source_id(advertiser_name: str, content_url: str) -> str:
    stable_url = urlparse(content_url).path  # 쿼리 파라미터 제거, path만 사용
    raw = f"meta:{advertiser_name}:{stable_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def extract_ads(page) -> list[dict]:
    """Extract ad data by splitting page sections between HR separators."""
    ads = []

    logger.info("JS evaluate로 광고 추출 시작")

    # Use page.evaluate to run extraction in browser context
    raw_ads = page.evaluate("""() => {
        const results = [];

        // Strategy: find all _7jyh containers (one per ad), limit to 30
        const adContainers = Array.from(document.querySelectorAll('div._7jyh')).slice(0, 200);

        for (const container of adContainers) {
            const ad = {};

            // Walk up to find the full ad section (parent divs up to the HR level)
            let adSection = container.closest('div.xh8yej3') || container.parentElement?.parentElement || container;

            // 1. Advertiser name: from img._8nqq alt attribute
            const profileImg = adSection.querySelector('img._8nqq');
            ad.advertiser_name = profileImg ? profileImg.alt : '';

            // Also try: span inside a link to facebook page
            if (!ad.advertiser_name) {
                const pageLink = adSection.querySelector('a[href*="facebook.com/"] span');
                if (pageLink) ad.advertiser_name = pageLink.textContent.trim();
            }

            // 2. Content URL and Thumbnail
            ad.content_url = '';
            ad.thumbnail_url = null;

            // Check for video first
            const videoContainer = adSection.querySelector('[data-testid="ad-content-body-video-container"]');
            if (videoContainer) {
                const video = videoContainer.querySelector('video');
                if (video) {
                    ad.content_url = video.src || '';
                    if (!ad.content_url) {
                        const source = video.querySelector('source');
                        if (source) ad.content_url = source.src || '';
                    }
                    ad.thumbnail_url = video.poster || null;
                }
            }
            // Direct video fallback
            if (!ad.content_url) {
                const videos = adSection.querySelectorAll('video');
                for (const v of videos) {
                    if (v.src) {
                        ad.content_url = v.src;
                        ad.thumbnail_url = v.poster || null;
                        break;
                    }
                    const s = v.querySelector('source');
                    if (s && s.src) {
                        ad.content_url = s.src;
                        ad.thumbnail_url = v.poster || null;
                        break;
                    }
                }
            }

            // If no video, use image as content_url
            if (!ad.content_url) {
                const images = adSection.querySelectorAll('img');
                for (const img of images) {
                    const src = img.src || '';
                    const cls = img.className || '';
                    if (cls.includes('_8nqq')) continue;
                    if (src.startsWith('data:')) continue;
                    if (src.includes('emoji')) continue;
                    if (src.includes('scontent') && src.includes('fbcdn.net') && !src.includes('s60x60')) {
                        ad.content_url = src;
                        ad.thumbnail_url = null;
                        break;
                    }
                }
                // fallback: any non-profile image
                if (!ad.content_url) {
                    const images2 = adSection.querySelectorAll('img');
                    for (const img of images2) {
                        const src = img.src || '';
                        const cls = img.className || '';
                        if (cls.includes('_8nqq')) continue;
                        if (!src.startsWith('data:') && !src.includes('emoji') && src.startsWith('http')) {
                            ad.content_url = src;
                            ad.thumbnail_url = null;
                            break;
                        }
                    }
                }
            }

            // 3. Landing page (CTA link)
            ad.landing_page_url = '';

            const ctaLink = adSection.querySelector('a[href*="l.facebook.com/l.php"]');
            if (ctaLink) {
                const href = ctaLink.href;
                try {
                    const url = new URL(href);
                    const u = url.searchParams.get('u');
                    ad.landing_page_url = u ? decodeURIComponent(u) : href;
                } catch(e) {
                    ad.landing_page_url = href;
                }
            }
            // Fallback: external link
            if (!ad.landing_page_url) {
                const allLinks = adSection.querySelectorAll('a[href]');
                for (const link of allLinks) {
                    const h = link.href || '';
                    if (h.startsWith('http') && !h.includes('facebook.com') && !h.includes('instagram.com')) {
                        ad.landing_page_url = h;
                        break;
                    }
                }
            }

            // Only add if we have some data
            if (ad.advertiser_name || ad.content_url) {
                results.push(ad);
            }
        }

        return results;
    }""")

    logger.info(f"_7jyh 컨테이너에서 {len(raw_ads)}건 추출")

    # If _7jyh didn't work, try alternative: find sections between <hr> tags
    if not raw_ads:
        logger.warning("_7jyh 컨테이너 0건, HR 기반 섹셔닝 시도")
        raw_ads = page.evaluate("""() => {
            const results = [];
            const hrs = Array.from(document.querySelectorAll('hr')).slice(0, 200);

            for (let i = 0; i < hrs.length; i++) {
                const hr = hrs[i];
                let section = hr.nextElementSibling;
                if (!section) continue;

                const ad = {};

                // Advertiser
                const profileImg = section.querySelector('img._8nqq');
                ad.advertiser_name = profileImg ? profileImg.alt : '';
                if (!ad.advertiser_name) {
                    const pageLink = section.querySelector('a[href*="facebook.com/"] span');
                    if (pageLink) ad.advertiser_name = pageLink.textContent.trim();
                }

                // Content URL and Thumbnail
                ad.content_url = '';
                ad.thumbnail_url = null;

                const video = section.querySelector('video');
                if (video) {
                    ad.content_url = video.src || '';
                    ad.thumbnail_url = video.poster || null;
                }

                if (!ad.content_url) {
                    const imgs = section.querySelectorAll('img');
                    for (const img of imgs) {
                        if (img.className.includes('_8nqq')) continue;
                        if (img.src && img.src.includes('scontent') && !img.src.includes('s60x60')) {
                            ad.content_url = img.src;
                            ad.thumbnail_url = null;
                            break;
                        }
                    }
                }

                // Landing page (CTA link)
                ad.landing_page_url = '';
                const cta = section.querySelector('a[href*="l.facebook.com/l.php"]');
                if (cta) {
                    try {
                        const url = new URL(cta.href);
                        ad.landing_page_url = decodeURIComponent(url.searchParams.get('u') || cta.href);
                    } catch(e) { ad.landing_page_url = cta.href; }
                }

                if (ad.advertiser_name || ad.content_url) {
                    results.push(ad);
                }
            }
            return results;
        }""")
        logger.info(f"HR 기반 섹셔닝에서 {len(raw_ads)}건 추출")

    if not raw_ads:
        logger.warning("광고 추출 0건: 두 가지 전략 모두 실패")

    return raw_ads


def raw_to_platform_ad(raw: dict) -> PlatformAd:
    content_url = raw.get("content_url", "")
    advertiser_name = raw.get("advertiser_name", "")
    poster_url = raw.get("thumbnail_url")  # video poster from <video poster="...">
    has_video = bool(poster_url) or "video" in (content_url or "").lower()
    media_type = "video" if has_video else "image"

    if media_type == "video":
        thumb = poster_url or ""
    else:
        thumb = content_url or ""

    return PlatformAd(
        source_id=make_source_id(advertiser_name, content_url),
        platform=PlatformType.meta,
        format=media_type,
        advertiser_name=advertiser_name,
        thumbnail_url=thumb,
        preview_url=content_url or None,
        media_type=media_type,
        landing_page_url=raw.get("landing_page_url") or None,
        raw_data=raw,
    )


def _scrape_meta_url(url: str, headless: bool = True, max_results: int = 500, existing_source_ids: set | None = None) -> list[PlatformAd]:
    """Shared Playwright browser logic for scraping Meta Ad Library URLs.

    Args:
        existing_source_ids: 이미 수집된 광고 source_id 집합.
            제공되면 스크롤 중 기존 광고 발견 시 조기 중단.
    """
    logger.info(f"Meta Ad Library 스크래핑 시작: url={url[:120]}, max_results={max_results}, incremental={'yes' if existing_source_ids else 'no'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        logger.info("페이지 로드 중 (networkidle, timeout 60s)")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Handle cookie consent dialog if it appears
        cookie_buttons = page.query_selector_all('button[data-cookiebanner="accept_button"]')
        if not cookie_buttons:
            cookie_buttons = page.query_selector_all('button[title="Allow all cookies"]')
        if not cookie_buttons:
            cookie_buttons = page.query_selector_all('button[title="모든 쿠키 허용"]')
        if cookie_buttons:
            logger.info("쿠키 동의 버튼 클릭")
            cookie_buttons[0].click()
            time.sleep(2)

        time.sleep(5)

        # Scroll down repeatedly to trigger lazy loading
        prev_height = 0
        prev_ad_count = 0
        max_scrolls = max(3, max_results // 5)
        for scroll_i in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break  # No more content to load
            prev_height = curr_height

            # 증분 모드: 매 3스크롤마다 기존 광고 존재 여부 체크 → 조기 중단
            if existing_source_ids and (scroll_i + 1) % 3 == 0:
                current_raw = extract_ads(page)
                if len(current_raw) > prev_ad_count:
                    new_raw = current_raw[prev_ad_count:]
                    new_platform = [raw_to_platform_ad(ad) for ad in new_raw]
                    has_existing = any(ad.source_id in existing_source_ids for ad in new_platform)
                    if has_existing:
                        logger.info(f"기존 광고 발견 → 스크롤 중단 (scroll {scroll_i + 1}, ads loaded: {len(current_raw)})")
                        break
                    prev_ad_count = len(current_raw)

        raw_ads = extract_ads(page)

        # Domain filtering
        filtered_ads = [
            ad for ad in raw_ads
            if not is_blocked_url(ad.get("landing_page_url", ""))
        ]
        removed_count = len(raw_ads) - len(filtered_ads)
        if removed_count > 0:
            logger.info(f"도메인 필터링: {removed_count}건 제거 (naver/kakao/facebook/instagram)")

        # Limit results
        filtered_ads = filtered_ads[:max_results]

        # Convert to PlatformAd
        platform_ads = [raw_to_platform_ad(ad) for ad in filtered_ads]
        logger.info(f"Meta 스크래핑 완료: {len(platform_ads)}건")

        browser.close()

    return platform_ads


def scrape_meta_ads(keyword: str, headless: bool = True, max_results: int = 500, existing_source_ids: set | None = None) -> list[PlatformAd]:
    encoded_keyword = quote(keyword)
    today = date.today()
    three_months_ago = _THREE_MONTHS_AGO
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=KR"
        f"&q={encoded_keyword}&search_type=keyword_unordered"
        f"&start_date[min]={three_months_ago.strftime('%Y-%m-%d')}"
        f"&start_date[max]={today.strftime('%Y-%m-%d')}"
    )
    return _scrape_meta_url(url, headless, max_results, existing_source_ids)


def scrape_meta_ads_by_page_id(page_id: str, headless: bool = True, max_results: int = 500, existing_source_ids: set | None = None) -> list[PlatformAd]:
    today = date.today()
    three_months_ago = _THREE_MONTHS_AGO
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=KR"
        f"&view_all_page_id={page_id}&search_type=page&media_type=all"
        f"&start_date[min]={three_months_ago.strftime('%Y-%m-%d')}"
        f"&start_date[max]={today.strftime('%Y-%m-%d')}"
    )
    return _scrape_meta_url(url, headless, max_results, existing_source_ids)


def parse_meta_page_id(input_value: str) -> str:
    """Extract page_id from various input formats (raw ID, Ad Library URL, profile URL)."""
    input_value = input_value.strip()
    if input_value.isdigit():
        return input_value
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(input_value)
    qs = parse_qs(parsed.query)
    if 'view_all_page_id' in qs:
        return qs['view_all_page_id'][0]
    if 'id' in qs:
        return qs['id'][0]
    return input_value


def main(keyword: str = "", page_id: str = "", headless: bool = True, max_results: int = 12) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if page_id:
        resolved_id = parse_meta_page_id(page_id)
        platform_ads = scrape_meta_ads_by_page_id(resolved_id, headless=headless, max_results=max_results)
        return {
            "page_id": resolved_id,
            "source": "meta_ad_library",
            "scraped_at": datetime.now().isoformat(),
            "total_count": len(platform_ads),
            "ads": [ad.model_dump(mode="json") for ad in platform_ads],
        }

    platform_ads = scrape_meta_ads(keyword, headless=headless, max_results=max_results)
    return {
        "keyword": keyword,
        "source": "meta_ad_library",
        "scraped_at": datetime.now().isoformat(),
        "total_count": len(platform_ads),
        "ads": [ad.model_dump(mode="json") for ad in platform_ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta Ad Library Scraper (PlatformAd)")
    parser.add_argument("--keyword", type=str, default="", help="Search keyword")
    parser.add_argument("--page-id", type=str, default="", help="Facebook page ID or Ad Library URL")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--max-results", type=int, default=12, help="Maximum number of results")
    args = parser.parse_args()

    result = main(keyword=args.keyword, page_id=args.page_id, headless=args.headless, max_results=args.max_results)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"meta_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
