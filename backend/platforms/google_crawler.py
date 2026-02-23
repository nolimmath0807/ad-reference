import argparse
import asyncio
import json
import re
from datetime import datetime, date
from pathlib import Path

from playwright.async_api import async_playwright
from dotenv import load_dotenv

from conn import get_db
from platforms.model import PlatformAd, PlatformType

load_dotenv()


async def crawl_google_ads(domain: str, max_ads: int = 20) -> list[PlatformAd]:
    """Crawl Google Ads Transparency Center for a domain."""
    ads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ko-KR"
        )
        page = await context.new_page()

        # 1. Go to listing page
        url = f"https://adstransparency.google.com/?region=anywhere&domain={domain}"
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # 2. Click "See all ads" button to expand the full grid
        try:
            see_all_btn = page.locator('material-button.grid-expansion-button')
            if await see_all_btn.count() > 0:
                await see_all_btn.first.click()
                print(f"[Google Crawler] Clicked 'See all ads' button")
                await page.wait_for_timeout(3000)
            else:
                print(f"[Google Crawler] No 'See all ads' button found (all ads may already be visible)")
        except Exception as e:
            print(f"[Google Crawler] Could not click 'See all ads': {e}")

        # 3. Scroll to load more ads
        prev_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 15  # safety limit

        while scroll_attempts < max_scroll_attempts:
            current_count = await page.evaluate('''() => {
                return document.querySelectorAll('creative-preview a[href*="/creative/"]').length;
            }''')

            print(f"[Google Crawler] Scroll {scroll_attempts + 1}: found {current_count} ads so far")

            if current_count >= max_ads:
                break

            if current_count == prev_count and scroll_attempts > 2:
                break

            prev_count = current_count

            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            scroll_attempts += 1

        # 4. Extract ad links from creative-preview elements
        ad_links = await page.evaluate('''() => {
            const cards = document.querySelectorAll('creative-preview a');
            return Array.from(cards).map(a => ({
                href: a.getAttribute('href'),
                label: a.getAttribute('aria-label') || ''
            })).filter(a => a.href && a.href.includes('/creative/'));
        }''')

        print(f"[Google Crawler] Found {len(ad_links)} ads for {domain}")

        # 5. Visit each detail page (limit to max_ads)
        for i, link_data in enumerate(ad_links[:max_ads]):
            href = link_data['href']
            detail_url = f"https://adstransparency.google.com{href}"

            try:
                ad_data = await _extract_ad_detail(page, detail_url)
                if ad_data:
                    ads.append(ad_data)
                    print(f"  [{i+1}/{min(len(ad_links), max_ads)}] {ad_data.advertiser_name} - {ad_data.format}")
            except Exception as e:
                print(f"  [{i+1}] Error: {e}")
                continue

            # Small delay between requests
            await page.wait_for_timeout(500)

        await browser.close()

    return ads


async def _extract_ad_detail(page, detail_url: str) -> PlatformAd | None:
    """Extract ad data from a detail page."""
    await page.goto(detail_url, wait_until="networkidle", timeout=20000)
    await page.wait_for_timeout(2000)

    data = await page.evaluate('''() => {
        // Advertiser name
        const advEl = document.querySelector('advertiser-name, .advertiser-name');
        const advertiser = advEl ? advEl.innerText.trim() : 'Unknown';

        // Get body text for format and date
        const bodyText = document.body.innerText;

        // Format
        const formatMatch = bodyText.match(/형식:\\s*(.+?)\\n/);
        const format = formatMatch ? formatMatch[1].trim() : 'unknown';

        // Last shown date
        const dateMatch = bodyText.match(/마지막 게재일:\\s*(.+?)\\n/);
        const lastShown = dateMatch ? dateMatch[1].trim() : null;

        // Get main ad image - broadened detection
        // Look for any large image, excluding known icons/UI elements
        const excludePatterns = ['flag', 'googlelogo', 'favicon', 'icon', 'arrow', 'chevron', 'close', 'search', 'menu'];
        const adCdnDomains = ['i.ytimg.com', 'ytimg.com', 'tpc.googlesyndication.com', 'googleusercontent.com'];
        const imgs = document.querySelectorAll('img');
        let adImage = null;

        function isLargeImage(img) {
            // Check naturalWidth/naturalHeight first
            if (img.naturalWidth > 100 && img.naturalHeight > 100) return true;
            // Fallback to HTML width/height attributes
            const w = parseInt(img.getAttribute('width') || '0', 10);
            const h = parseInt(img.getAttribute('height') || '0', 10);
            if (w > 100 && h > 100) return true;
            return false;
        }

        function isAdCdnImage(src) {
            const srcLower = src.toLowerCase();
            return adCdnDomains.some(domain => srcLower.includes(domain));
        }

        // First pass: prefer images inside creative-preview or creative container
        const creativeArea = document.querySelector('creative-preview, .creative-preview, .creative-container, [class*="creative"]');
        if (creativeArea) {
            const creativeImgs = creativeArea.querySelectorAll('img');
            for (const img of creativeImgs) {
                if (!img.src) continue;
                const srcLower = img.src.toLowerCase();
                const isExcluded = excludePatterns.some(p => srcLower.includes(p));
                if (isExcluded) continue;
                // Accept if large OR from a known ad CDN
                if (isLargeImage(img) || isAdCdnImage(img.src)) {
                    adImage = img.src;
                    break;
                }
            }
        }

        // Second pass: separate by source (syndication vs other)
        let adImageSyndication = null;
        let adImageOther = null;
        if (!adImage) {
            for (const img of imgs) {
                if (!img.src) continue;
                const srcLower = img.src.toLowerCase();
                const isExcluded = excludePatterns.some(p => srcLower.includes(p));
                if (isExcluded) continue;
                if (isLargeImage(img) || isAdCdnImage(img.src)) {
                    if (srcLower.includes('googlesyndication.com') && !adImageSyndication) {
                        adImageSyndication = img.src;
                    } else if (!adImageOther) {
                        adImageOther = img.src;
                    }
                    if (adImageSyndication && adImageOther) break;
                }
            }
        }

        // Get video if exists
        const video = document.querySelector('video');
        const videoSrc = video ? (video.src || video.querySelector('source')?.src) : null;
        let videoPoster = video ? video.poster : null;

        // Extended video poster detection
        if (!videoPoster || videoPoster === '') {
            // Check for background-image on video container elements
            const videoContainers = document.querySelectorAll(
                '[class*="video"], [class*="player"], [class*="media"], [class*="creative"]'
            );
            for (const container of videoContainers) {
                // Check background-image CSS
                const style = window.getComputedStyle(container);
                const bgImage = style.backgroundImage;
                if (bgImage && bgImage !== 'none') {
                    const urlMatch = bgImage.match(/url\\(["']?(.+?)["']?\\)/);
                    if (urlMatch && urlMatch[1]) {
                        videoPoster = urlMatch[1];
                        break;
                    }
                }
                // Check for <img> inside video wrapper
                const innerImg = container.querySelector('img');
                if (innerImg && innerImg.src && innerImg.naturalWidth > 50) {
                    videoPoster = innerImg.src;
                    break;
                }
            }
        }

        // Extract YouTube video IDs from ALL images on the page
        const youtubeVideoIds = [];
        const ytRegex = /i\\.ytimg\\.com\\/vi\\/([a-zA-Z0-9_-]+)\\//;
        const allImgs = document.querySelectorAll('img');
        for (const img of allImgs) {
            if (!img.src) continue;
            const ytMatch = img.src.match(ytRegex);
            if (ytMatch && ytMatch[1] && !youtubeVideoIds.includes(ytMatch[1])) {
                youtubeVideoIds.push(ytMatch[1]);
            }
        }

        // Detect search ads by content patterns
        let isSearchAd = false;

        // Check body text for explicit text/search ad format indicators
        const searchAdPatterns = ['텍스트', 'Text'];
        for (const pattern of searchAdPatterns) {
            if (bodyText.includes('형식: ' + pattern) || bodyText.includes('Format: ' + pattern)) {
                isSearchAd = true;
                break;
            }
        }

        // Additional heuristic: if no visual creative found at all, likely a search/text ad
        if (!adImage && !adImageSyndication && !adImageOther && youtubeVideoIds.length === 0) {
            isSearchAd = true;
        }

        // Extract IDs from URL
        const url = window.location.href;
        const advIdMatch = url.match(/advertiser\\/(AR\\w+)/);
        const creativeIdMatch = url.match(/creative\\/(CR\\w+)/);

        return {
            advertiser,
            format,
            lastShown,
            adImage,
            adImageSyndication,
            adImageOther,
            videoSrc,
            videoPoster,
            youtubeVideoIds,
            isSearchAd,
            advertiserId: advIdMatch ? advIdMatch[1] : null,
            creativeId: creativeIdMatch ? creativeIdMatch[1] : null,
            url: url
        };
    }''')

    if not data.get('creativeId'):
        return None

    # DEBUG: Print raw JS data for diagnosis
    print(f"  [DEBUG] {data.get('creativeId')}: adImage={repr(data.get('adImage'))}, adImageSyndication={repr(data.get('adImageSyndication'))}, adImageOther={repr(data.get('adImageOther'))}, videoPoster={repr(data.get('videoPoster'))}, youtubeVideoIds={data.get('youtubeVideoIds', [])}")

    # 1. Determine format FIRST (needed for thumbnail priority)
    raw_format = data.get('format', 'unknown').lower()
    if '동영상' in raw_format or 'video' in raw_format:
        ad_format = 'video'
        media_type = 'video'
    elif '이미지' in raw_format or 'image' in raw_format:
        ad_format = 'image'
        media_type = 'image'
    elif '텍스트' in raw_format or 'text' in raw_format:
        ad_format = 'text'
        media_type = 'image'
    else:
        ad_format = 'image'
        media_type = 'image'

    # Skip text/search ads
    if ad_format == 'text' or data.get('isSearchAd', False):
        print(f"  [Skip] Search/text ad {data.get('creativeId')} - not a display ad (format={ad_format}, isSearchAd={data.get('isSearchAd', False)})")
        return None

    # 2. Determine thumbnail based on format
    youtube_ids = data.get('youtubeVideoIds', [])

    # Additional search ad detection: video format but no actual video content
    if ad_format == 'video' and not youtube_ids and not data.get('videoSrc'):
        # "Video" format but no actual video - likely a misclassified search ad
        # Check if the only image is from googlesyndication (text ad rendering)
        syndication_img = data.get('adImageSyndication', '')
        other_img = data.get('adImageOther', '')
        if not other_img or 'googlesyndication.com' in (other_img or ''):
            print(f"  [Skip] Likely search ad {data.get('creativeId')} - video format but no video content, only syndication thumbnail")
            return None

    if ad_format == 'video':
        # Video ads: prefer YouTube > syndication > other > screenshot
        if youtube_ids:
            video_id = youtube_ids[0]
            thumbnail_url = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
            youtube_embed = f'https://www.youtube.com/embed/{video_id}'
        else:
            thumbnail_url = data.get('adImage') or data.get('adImageSyndication') or data.get('adImageOther') or data.get('videoPoster') or ''
            youtube_embed = None
    else:
        # Image/text ads: prefer syndication > adImage > other > screenshot
        thumbnail_url = data.get('adImage') or data.get('adImageSyndication') or data.get('adImageOther') or data.get('videoPoster') or ''
        youtube_embed = None

    # Screenshot fallback if still no thumbnail
    if not thumbnail_url:
        thumbnail_url = await _screenshot_fallback(page, data['creativeId'])

    # 3. Determine preview URL
    if ad_format == 'video' and youtube_embed:
        preview_url = youtube_embed
    else:
        preview_url = data.get('videoSrc') or data.get('url')

    print(f"  [DEBUG] {data.get('creativeId')}: thumbnail_url={repr(thumbnail_url[:80] if thumbnail_url else 'EMPTY')}, preview_url={repr(preview_url[:80] if preview_url else 'EMPTY')}")

    return PlatformAd(
        source_id=data['creativeId'],
        platform=PlatformType.google,
        format=ad_format,
        advertiser_name=data.get('advertiser', 'Unknown'),
        advertiser_handle=data.get('advertiserId'),
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        media_type=media_type,
        ad_copy=None,
        cta_text=None,
        start_date=None,
        end_date=None,
        landing_page_url=None,
        tags=[],
        raw_data=data,
    )


async def _screenshot_fallback(page, creative_id: str) -> str:
    """Take a viewport screenshot of the creative preview area as thumbnail fallback."""
    print(f"  [Screenshot] Taking fallback screenshot for {creative_id}...")
    screenshots_dir = Path(__file__).parent.parent / "static" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshots_dir / f"{creative_id}.png"

    try:
        await page.screenshot(
            path=str(screenshot_path),
            clip={"x": 250, "y": 200, "width": 780, "height": 550},
        )
        print(f"  [Screenshot] Saved: {screenshot_path}")
        return f"/static/screenshots/{creative_id}.png"
    except Exception:
        print(f"  [Screenshot] Failed for {creative_id}")
        return ''


def save_crawled_ads(ads: list[PlatformAd]) -> int:
    """Save crawled ads to database."""
    if not ads:
        return 0

    saved = 0
    with get_db() as (conn, cur):
        for ad in ads:
            cur.execute(
                """
                INSERT INTO ads (
                    source_id, platform, format, advertiser_name,
                    advertiser_handle, thumbnail_url, preview_url,
                    media_type, ad_copy, cta_text,
                    start_date, end_date, tags,
                    landing_page_url
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s
                )
                ON CONFLICT (source_id, platform) DO UPDATE SET
                    advertiser_name = EXCLUDED.advertiser_name,
                    thumbnail_url = EXCLUDED.thumbnail_url,
                    preview_url = EXCLUDED.preview_url,
                    ad_copy = EXCLUDED.ad_copy
                """,
                (
                    ad.source_id, ad.platform.value, ad.format,
                    ad.advertiser_name, ad.advertiser_handle,
                    ad.thumbnail_url, ad.preview_url,
                    ad.media_type, ad.ad_copy, ad.cta_text,
                    ad.start_date, ad.end_date,
                    ad.tags, ad.landing_page_url,
                ),
            )
            saved += 1

    return saved


def main(domains: list[str], max_per_domain: int = 20) -> dict:
    """Crawl Google Ads for multiple domains."""
    all_ads = []
    results = {"domains": {}, "total": 0, "saved": 0}

    for domain in domains:
        print(f"\n[Google Crawler] Crawling {domain}...")
        ads = asyncio.run(crawl_google_ads(domain, max_ads=max_per_domain))
        all_ads.extend(ads)
        results["domains"][domain] = len(ads)

    saved = save_crawled_ads(all_ads)
    results["total"] = len(all_ads)
    results["saved"] = saved
    results["crawled_at"] = datetime.now().isoformat()

    print(f"\n[Google Crawler] Total: {len(all_ads)} ads, Saved: {saved}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Ads Transparency Center Crawler")
    parser.add_argument("--domains", required=True, nargs="+", help="Domains to crawl (e.g., nike.com coupang.com)")
    parser.add_argument("--max", type=int, default=20, help="Max ads per domain (default: 20)")
    args = parser.parse_args()

    result = main(args.domains, max_per_domain=args.max)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"google_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
