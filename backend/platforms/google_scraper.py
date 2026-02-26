import argparse
import hashlib
import json
import logging
import re
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from playwright.sync_api import sync_playwright

from conn import get_db
from platforms.model import PlatformAd, PlatformType

logger = logging.getLogger("google_scraper")

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
    raw = f"google:{advertiser_name}:{content_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def extract_creative_id_from_link(href: str) -> str | None:
    """creative 링크에서 ID 추출: /creative/CR01534115872354861057 → CR01534115872354861057"""
    m = re.search(r'/creative/(CR\w+)', href)
    return m.group(1) if m else None


def get_existing_creative_ids(domain: str) -> set[str]:
    """DB에서 해당 도메인의 기존 creative_id 목록 조회"""
    bare_domain = domain.replace("www.", "")
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT creative_id FROM ads
            WHERE platform = 'google'
              AND creative_id IS NOT NULL
              AND (REPLACE(domain, 'www.', '') = %s
                   OR (domain IS NULL AND landing_page_url LIKE %s))
            """,
            (bare_domain, f"%{bare_domain}%"),
        )
        return {row[0] for row in cur.fetchall()}


def _is_junk_url(url: str) -> bool:
    """content_url로 쓸모없는 URL인지 판별"""
    if not url:
        return True
    lower = url.lower()
    if "safeframe" in lower:
        return True
    if lower.rstrip("/").endswith("/adframe"):
        return True
    if lower.startswith("about:"):
        return True
    return False


def _extract_youtube_video_id(url: str) -> str | None:
    """다양한 YouTube 관련 URL에서 video ID를 추출"""
    if not url:
        return None
    # ytimg.com/vi/{VIDEO_ID}/... 패턴
    m = re.search(r'ytimg\.com/vi/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtube.com/watch?v={VIDEO_ID}
    m = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtube.com/embed/{VIDEO_ID}
    m = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtu.be/{VIDEO_ID}
    m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    # youtube_vertical_player_media 등 URL 내 video_id 파라미터
    m = re.search(r'[?&]video_id=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    return None


def collect_all_variants(page) -> list[dict]:
    """creative-details .ad-container의 모든 대안 sub-container에서 content_url 일괄 수집
    (모든 대안이 DOM에 동시에 로드되어 있음 - hidden 클래스로 표시 제어)
    각 variant에 landing_url 후보(anchor href)도 함께 수집

    수집 우선순위:
    1. img[src*="simgad"] - 직접 이미지
    2. iframe[src*="youtube"] - 유튜브 영상
    3. iframe[src*="sadbundle"] - sadbundle (adurl 추출 가능)
    4. adframe iframe 내부 진입 -> simgad 이미지 추출
    5. safeframe iframe은 content_url 후보에서 제외
    """
    raw = page.evaluate("""() => {
        const container = document.querySelector('creative-details .ad-container');
        if (!container) return [];

        const results = [];
        const seen = new Set();
        const skipDomains = ['adstransparency.google.com', 'support.google.com',
                              'policies.google.com', 'safety.google', 'about.google'];

        // 형식 라벨 감지 (creative-details 영역 내)
        const allBodyText = document.body ? document.body.innerText : '';
        const isTextAd = /형식\\s*[:\\uff1a]\\s*텍스트|Format\\s*[:\\uff1a]\\s*Text/i.test(allBodyText);

        // 모든 대안 sub-container 순회 (visible/hidden 모두 포함)
        const subs = container.querySelectorAll('.creative-sub-container');
        const targets = subs.length > 0 ? Array.from(subs) : [container];

        // YouTube video ID 추출 헬퍼 (JS 내부)
        function extractYtVideoId(src) {
            if (!src) return null;
            let m;
            m = src.match(/ytimg\\.com\\/vi\\/([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            m = src.match(/youtube\\.com\\/embed\\/([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            m = src.match(/youtube\\.com\\/watch\\?v=([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            m = src.match(/youtu\\.be\\/([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            m = src.match(/[?&]video_id=([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            return null;
        }

        for (const sub of targets) {
            let url = null;
            let is_video = false;
            let video_url = null;
            let thumb_url = null;
            let youtube_video_id = null;

            // 영상 감지: sub-container 내 video/iframe 관련 요소 확인
            const ytIframeCheck = sub.querySelector('iframe[src*="youtube"]');
            const ytVerticalCheck = sub.querySelector('iframe[src*="youtube_vertical_player"]');
            const videoTagCheck = sub.querySelector('video');
            if (ytIframeCheck || ytVerticalCheck || videoTagCheck) {
                is_video = true;
            }

            // 영상 광고: thumbnail_url과 video_url 분리 수집
            if (is_video) {
                // 썸네일: ytimg.com 이미지 또는 simgad 이미지
                const ytThumb = sub.querySelector('img[src*="ytimg"]');
                if (ytThumb && ytThumb.src) {
                    thumb_url = ytThumb.src;
                    // ytimg URL에서 video ID 추출
                    if (!youtube_video_id) youtube_video_id = extractYtVideoId(ytThumb.src);
                }
                if (!thumb_url) {
                    const simgadThumb = sub.querySelector('img[src*="simgad"]');
                    if (simgadThumb && simgadThumb.src) thumb_url = simgadThumb.src;
                }

                // 영상 플레이어 URL: YouTube iframe src 또는 youtube_vertical_player iframe src
                if (ytVerticalCheck && ytVerticalCheck.src) {
                    video_url = ytVerticalCheck.src;
                    if (!youtube_video_id) youtube_video_id = extractYtVideoId(ytVerticalCheck.src);
                } else if (ytIframeCheck && ytIframeCheck.src) {
                    video_url = ytIframeCheck.src;
                    if (!youtube_video_id) youtube_video_id = extractYtVideoId(ytIframeCheck.src);
                }
                if (videoTagCheck && !video_url) {
                    const videoSrc = videoTagCheck.src || videoTagCheck.querySelector('source')?.src;
                    if (videoSrc) video_url = videoSrc;
                }
            }

            // 1순위: 직접 simgad 이미지
            const img = sub.querySelector('img[src*="simgad"]');
            if (img && img.src) url = img.src;

            // 2순위: YouTube iframe
            const ytIframe = sub.querySelector('iframe[src*="youtube"]');
            if (!url && ytIframe && ytIframe.src) url = ytIframe.src;

            // 3순위: sadbundle iframe
            const sbIframe = sub.querySelector('iframe[src*="sadbundle"]');
            if (!url && sbIframe && sbIframe.src) url = sbIframe.src;

            // 4순위: adframe iframe 내부에서 simgad 이미지 탐색
            if (!url) {
                const adframeIframe = sub.querySelector('iframe[src*="adframe"]');
                if (adframeIframe) {
                    try {
                        const innerDoc = adframeIframe.contentDocument || adframeIframe.contentWindow.document;
                        if (innerDoc) {
                            const innerImg = innerDoc.querySelector('img[src*="simgad"]');
                            if (innerImg && innerImg.src) url = innerImg.src;
                            // adframe 내부의 다른 iframe에서도 탐색
                            if (!url) {
                                const innerIframes = innerDoc.querySelectorAll('iframe[src]');
                                for (const f of innerIframes) {
                                    if (f.src && (f.src.includes('simgad') || f.src.includes('youtube'))) {
                                        url = f.src;
                                        break;
                                    }
                                }
                            }
                            // adframe 내부에서도 영상 감지
                            if (!is_video) {
                                const innerYt = innerDoc.querySelector('iframe[src*="youtube"]');
                                const innerVideo = innerDoc.querySelector('video');
                                if (innerYt || innerVideo) {
                                    is_video = true;
                                    if (innerYt && innerYt.src) {
                                        video_url = innerYt.src;
                                        if (!youtube_video_id) youtube_video_id = extractYtVideoId(innerYt.src);
                                    }
                                    const innerThumb = innerDoc.querySelector('img[src*="ytimg"]');
                                    if (innerThumb && innerThumb.src) {
                                        thumb_url = innerThumb.src;
                                        if (!youtube_video_id) youtube_video_id = extractYtVideoId(innerThumb.src);
                                    }
                                }
                            }
                        }
                    } catch(e) {
                        // cross-origin 접근 불가 시 무시
                    }
                }
            }

            // 5순위: 기타 iframe (safeframe/adframe/about: 제외)
            if (!url) {
                const allIframes = sub.querySelectorAll('iframe[src]');
                for (const f of allIframes) {
                    const s = f.src.toLowerCase();
                    if (s && !s.includes('safeframe') && !s.includes('adframe')
                        && !s.startsWith('about:')) {
                        url = f.src;
                        break;
                    }
                }
            }

            // sub-container 내 <a> 태그에서 외부 링크 수집 (랜딩 URL 후보)
            let anchor_href = null;
            const anchors = sub.querySelectorAll('a[href]');
            for (const a of anchors) {
                const h = a.href;
                if (h && h.startsWith('http') && !skipDomains.some(d => h.includes(d))) {
                    anchor_href = h;
                    break;
                }
            }

            // content_url에서도 youtube_video_id 추출 시도
            if (!youtube_video_id && url) youtube_video_id = extractYtVideoId(url);

            if (url && !seen.has(url)) {
                seen.add(url);
                results.push({
                    content_url: url,
                    anchor_href: anchor_href,
                    is_video: is_video,
                    is_text: isTextAd && !is_video,
                    ad_copy_text: (isTextAd && !is_video) ? sub.innerText.trim() : null,
                    video_url: video_url,
                    thumbnail_url: thumb_url,
                    youtube_video_id: youtube_video_id,
                });
            }

            // 텍스트 광고 처리: 형식이 텍스트이고 이미지/비디오 URL이 없는 경우
            if (!url && isTextAd) {
                const textContent = sub.innerText.trim();
                if (textContent) {
                    const syntheticId = 'text_ad:' + btoa(unescape(encodeURIComponent(textContent.substring(0, 100))));
                    if (!seen.has(syntheticId)) {
                        seen.add(syntheticId);
                        results.push({
                            content_url: syntheticId,
                            anchor_href: anchor_href,
                            is_video: false,
                            is_text: true,
                            ad_copy_text: textContent,
                            video_url: null,
                            thumbnail_url: null,
                            youtube_video_id: null,
                        });
                    }
                }
            }
        }

        return results;
    }""")

    # Python 측에서 쓸모없는 URL 최종 필터링 (텍스트 광고는 content_url 필터 제외)
    return [v for v in raw if v.get("is_text") or not _is_junk_url(v.get("content_url", ""))]


def _collect_variants_from_frames(page) -> list[dict]:
    """Playwright frame API로 iframe 내부에서 simgad 이미지, 링크 등 추출.
    JS evaluate로 cross-origin iframe에 접근 불가할 때 fallback으로 사용.
    """
    results = []
    seen = set()

    for frame in page.frames:
        frame_url = frame.url
        # 메인 프레임 스킵
        if frame == page.main_frame:
            continue

        # safeframe/adframe 내부에 접근하여 실제 콘텐츠 URL 찾기
        content_url = None
        anchor_href = None
        is_video = False
        video_url = None
        thumb_url = None
        youtube_video_id = None

        # 영상 감지: frame 내부의 video/youtube 요소 확인
        yt_iframes = frame.query_selector_all('iframe[src*="youtube"]')
        yt_vertical_iframes = frame.query_selector_all('iframe[src*="youtube_vertical_player"]')
        video_tags = frame.query_selector_all('video')
        if yt_iframes or yt_vertical_iframes or video_tags:
            is_video = True
            # 영상 플레이어 URL 수집
            for yt_v in yt_vertical_iframes:
                src = yt_v.get_attribute("src")
                if src:
                    video_url = src
                    if not youtube_video_id:
                        youtube_video_id = _extract_youtube_video_id(src)
                    break
            if not video_url:
                for yt_i in yt_iframes:
                    src = yt_i.get_attribute("src")
                    if src:
                        video_url = src
                        if not youtube_video_id:
                            youtube_video_id = _extract_youtube_video_id(src)
                        break
            if not video_url:
                for vt in video_tags:
                    src = vt.get_attribute("src")
                    if src:
                        video_url = src
                        break
                    source_el = vt.query_selector("source[src]")
                    if source_el:
                        src = source_el.get_attribute("src")
                        if src:
                            video_url = src
                            break
            # 썸네일 수집
            ytimg_imgs = frame.query_selector_all('img[src*="ytimg"]')
            for img in ytimg_imgs:
                src = img.get_attribute("src")
                if src:
                    thumb_url = src
                    if not youtube_video_id:
                        youtube_video_id = _extract_youtube_video_id(src)
                    break

        # 1. frame 내부의 simgad 이미지
        simgad_imgs = frame.query_selector_all('img[src*="simgad"]')
        for img in simgad_imgs:
            src = img.get_attribute("src")
            if src:
                content_url = src
                break

        # 2. frame 내부의 또 다른 iframe (중첩)
        if not content_url:
            inner_iframes = frame.query_selector_all('iframe[src]')
            for inner in inner_iframes:
                src = inner.get_attribute("src")
                if src and ("simgad" in src or "youtube" in src):
                    content_url = src
                    break

        # 3. frame 내부의 일반 이미지 (충분히 큰 것만)
        if not content_url:
            all_imgs = frame.query_selector_all("img[src]")
            for img in all_imgs:
                src = img.get_attribute("src")
                if src and src.startswith("http") and "googlesyndication" not in src:
                    content_url = src
                    break

        # frame 내부 외부 링크 수집 (랜딩 URL 후보)
        skip_domains = ["adstransparency.google.com", "support.google.com",
                        "policies.google.com", "safety.google", "about.google",
                        "blog.google", "googlesyndication.com", "safeframe"]
        anchors = frame.query_selector_all("a[href]")
        for a in anchors:
            href = a.get_attribute("href")
            if href and href.startswith("http") and not any(d in href for d in skip_domains):
                anchor_href = href
                break

        # content_url에서도 youtube_video_id 추출 시도
        if not youtube_video_id and content_url:
            youtube_video_id = _extract_youtube_video_id(content_url)

        if content_url and content_url not in seen and not _is_junk_url(content_url):
            seen.add(content_url)
            results.append({
                "content_url": content_url,
                "anchor_href": anchor_href,
                "is_video": is_video,
                "video_url": video_url,
                "thumbnail_url": thumb_url,
                "youtube_video_id": youtube_video_id,
            })

    return results


def get_landing_from_sadbundle(page, sadbundle_url: str) -> str:
    """sadbundle 방문 -> HTML에서 adurl= 파라미터 추출 -> 랜딩 URL 디코딩"""
    page.goto(sadbundle_url, wait_until="load", timeout=15000)
    time.sleep(2)

    html = page.content()
    match = re.search(r"adurl=(https?[^\"&<>\s\\]+)", html)
    if match:
        return urllib.parse.unquote(match.group(1))
    return ""


def _extract_landing_url(page) -> str:
    """상세 페이지에서 랜딩 URL을 추출하는 헬퍼.
    여러 전략을 순차 시도:
    1. 페이지 내 '대상' / 'Destination' 라벨 옆 URL 텍스트
    2. creative-details 영역 내 외부 <a> 링크
    3. 페이지 전체에서 googleadservices.com 리다이렉트 URL의 adurl= 파라미터
    """
    result = page.evaluate("""() => {
        // 전략 1: '대상' 또는 'Destination' 라벨 근처 URL
        const allText = document.body ? document.body.innerText : '';
        const destMatch = allText.match(/(?:대상|Destination)[:\\s]*(https?:\\/\\/[^\\s]+)/i);
        if (destMatch) return destMatch[1];

        // 전략 2: creative-details 내 외부 <a> 링크
        const skipDomains = [
            'adstransparency.google.com',
            'support.google.com',
            'policies.google.com',
            'safety.google',
            'google.com/ads',
            'about.google',
            'blog.google',
            'googlesyndication.com',
        ];
        const details = document.querySelector('creative-details');
        if (details) {
            const links = details.querySelectorAll('a[href]');
            for (const a of links) {
                const h = a.href;
                if (h && h.startsWith('http')
                    && !skipDomains.some(d => h.includes(d))) {
                    return h;
                }
            }
        }

        // 전략 3: 페이지 내 googleadservices 리다이렉트에서 adurl= 추출
        const html = document.documentElement.innerHTML;
        const adservicesMatch = html.match(/googleadservices\\.com[^"']*adurl=(https?[^"&<>\\s\\\\]+)/);
        if (adservicesMatch) return decodeURIComponent(adservicesMatch[1]);

        return '';
    }""")
    return result or ""


def variant_to_platform_ad(advertiser_name: str, variant: dict, landing_url: str) -> PlatformAd:
    # 텍스트 광고 처리
    is_text = variant.get("is_text", False)
    if is_text:
        ad_copy_text = variant.get("ad_copy_text", "")
        content_url = variant.get("content_url", "")

        # content_url이 실제 이미지 URL이면 make_source_id 사용, synthetic ID면 텍스트 해시
        if content_url and not content_url.startswith("text_ad:"):
            source_id = make_source_id(advertiser_name, content_url)
        else:
            content_key = f"text:{advertiser_name}:{ad_copy_text[:100]}"
            source_id = hashlib.sha256(f"google:{content_key}".encode()).hexdigest()[:16]

        domain = ""
        if landing_url:
            m = re.match(r'https?://(?:www\.)?([^/]+)', landing_url)
            if m:
                domain = m.group(1)

        return PlatformAd(
            source_id=source_id,
            platform=PlatformType.google,
            format="text",
            advertiser_name=advertiser_name,
            thumbnail_url=content_url if content_url and not content_url.startswith("text_ad:") else "",
            preview_url=None,
            media_type="text",
            ad_copy=ad_copy_text,
            landing_page_url=landing_url or None,
            domain=domain,
            raw_data={"advertiser_name": advertiser_name, "variant": variant},
        )

    # 기존 video/image 로직
    content_url = variant.get("content_url", "")
    lower_url = content_url.lower()

    # 영상 판별: JS에서 전달한 is_video 힌트 + URL 키워드 기반 판별 병용
    is_video = variant.get("is_video", False) or any(keyword in lower_url for keyword in [
        "youtube.com", "youtu.be", "ytimg.com",
        "youtube_vertical_player", "youtube_player",
        "video_player",
    ])
    media_type = "video" if is_video else "image"

    # YouTube video ID 추출: variant에서 직접 가져오거나 URL들에서 추출
    video_id = variant.get("youtube_video_id")
    if not video_id:
        for url_key in ("content_url", "thumbnail_url", "video_url"):
            video_id = _extract_youtube_video_id(variant.get(url_key, ""))
            if video_id:
                break

    # 영상 광고: thumbnail_url은 썸네일 이미지, preview_url은 실제 YouTube 영상 URL
    # 이미지 광고: 둘 다 content_url 사용
    if is_video and video_id:
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
        preview_url = f"https://www.youtube.com/watch?v={video_id}"
    elif is_video:
        thumbnail_url = variant.get("thumbnail_url") or content_url or ""
        preview_url = variant.get("video_url") or content_url or None
    else:
        thumbnail_url = content_url or ""
        preview_url = content_url or None

    # Extract domain from landing_url (www. 접두사 제거하여 정규화)
    domain = ""
    if landing_url:
        m = re.match(r'https?://(?:www\.)?([^/]+)', landing_url)
        if m:
            domain = m.group(1)

    return PlatformAd(
        source_id=make_source_id(advertiser_name, content_url),
        platform=PlatformType.google,
        format=media_type,
        advertiser_name=advertiser_name,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        media_type=media_type,
        landing_page_url=landing_url or None,
        domain=domain,
        raw_data={"advertiser_name": advertiser_name, "variant": variant},
    )


def _search_and_get_advertisers(page, keyword: str, base_url: str) -> list[dict]:
    """키워드 검색 후 드롭다운에서 광고주 목록(이름 + 인덱스)을 수집한다."""
    page.goto(base_url, wait_until="load", timeout=60000)
    time.sleep(5)

    search_input = page.wait_for_selector('input[type="text"]', timeout=15000)
    search_input.click()
    search_input.fill(keyword)
    time.sleep(1)

    page.wait_for_selector("material-select-item", timeout=15000)
    time.sleep(1)

    items = page.query_selector_all("material-select-item")
    advertisers = []
    for idx, item in enumerate(items):
        name_el = item.query_selector("div.name")
        name = name_el.inner_text().strip() if name_el else f"Unknown_{idx}"
        advertisers.append({"name": name, "index": idx})

    return advertisers


def _collect_ads_for_advertiser(
    page, keyword: str, base_url: str, advertiser_index: int, advertiser_name: str, max_creatives: int
) -> list[PlatformAd]:
    """검색 페이지에서 특정 광고주를 클릭하고 광고를 수집한다."""
    # 검색 페이지로 이동 + 키워드 입력 + 드롭다운 대기
    page.goto(base_url, wait_until="load", timeout=60000)
    time.sleep(5)

    search_input = page.wait_for_selector('input[type="text"]', timeout=15000)
    search_input.click()
    search_input.fill(keyword)
    time.sleep(1)

    page.wait_for_selector("material-select-item", timeout=15000)
    time.sleep(1)

    items = page.query_selector_all("material-select-item")
    if advertiser_index >= len(items):
        logger.warning(f"광고주 인덱스 {advertiser_index} 초과 (총 {len(items)}개)")
        return []

    target_item = items[advertiser_index]
    logger.info(f"광고주 클릭: {advertiser_name} (index={advertiser_index})")
    target_item.click()

    # 광고 카드 로드 대기
    logger.info("creative-preview 카드 대기")
    page.wait_for_selector("creative-preview", timeout=30000)
    time.sleep(3)

    # 크리에이티브 링크 수집
    creatives = page.query_selector_all("creative-preview")[:max_creatives]
    logger.info(f"creative-preview {len(creatives)}개 발견")

    creative_links = []
    for creative in creatives:
        link_el = creative.query_selector("a[href]")
        if link_el:
            href = link_el.get_attribute("href")
            creative_links.append(href)

    logger.info(f"크리에이티브 링크 {len(creative_links)}개 수집")

    # 각 크리에이티브 상세 페이지 방문 -> 대안별 URL 수집 -> 랜딩 URL 추출
    ads: list[PlatformAd] = []

    for i, href in enumerate(creative_links):
        detail_url = f"https://adstransparency.google.com{href}"
        if "region=KR" not in detail_url:
            detail_url += ("&" if "?" in detail_url else "?") + "region=KR"

        logger.info(f"  [{i+1}/{len(creative_links)}] 상세 페이지: {href[:80]}")

        try:
            page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"  [{i+1}/{len(creative_links)}] 상세 페이지 로드 실패, skip: {e}")
            continue
        time.sleep(3)

        # 광고주명
        name_el = page.query_selector("div.advertiser-name")
        name = name_el.inner_text().strip() if name_el else advertiser_name

        # creative-details 패널 대기
        try:
            page.wait_for_selector("creative-details .ad-container", timeout=5000)
        except Exception:
            logger.warning(f"creative-details 패널 없음: url={detail_url[:100]}")
            continue

        # 실제 광고 콘텐츠(simgad 이미지 또는 youtube iframe)가 로드될 때까지 추가 대기
        try:
            page.wait_for_selector(
                'creative-details img[src*="simgad"], '
                'creative-details iframe[src*="youtube"], '
                'creative-details iframe[src*="sadbundle"]',
                timeout=5000,
            )
        except Exception:
            logger.debug("simgad/youtube/sadbundle 콘텐츠 미감지, 기존 DOM으로 진행")
        time.sleep(1)

        # 모든 대안 수집 (JS evaluate + Playwright frame API 병용)
        raw_variants = collect_all_variants(page)

        # JS로 못 찾은 경우 Playwright frame API로 iframe 내부 콘텐츠 탐색
        if not raw_variants:
            raw_variants = _collect_variants_from_frames(page)

        # 텍스트 광고 fallback: 이미지/영상 variant가 없지만 페이지에 텍스트 콘텐츠가 있는 경우
        if not raw_variants:
            is_text_format = page.evaluate("""() => {
                const bodyText = document.body ? document.body.innerText : '';
                return /형식\\s*[:\\uff1a]\\s*텍스트|Format\\s*[:\\uff1a]\\s*Text/i.test(bodyText);
            }""")
            if is_text_format:
                ad_text = page.evaluate("""() => {
                    const container = document.querySelector('creative-details .ad-container');
                    return container ? container.innerText.trim() : '';
                }""")
                if ad_text:
                    raw_variants = [{
                        "content_url": "text_ad:" + hashlib.sha256(ad_text[:100].encode()).hexdigest()[:16],
                        "anchor_href": None,
                        "is_video": False,
                        "is_text": True,
                        "ad_copy_text": ad_text,
                        "video_url": None,
                        "thumbnail_url": None,
                        "youtube_video_id": None,
                    }]
                    logger.info(f"  텍스트 광고 감지: {ad_text[:80]}")

        logger.info(f"  {name} | 대안 {len(raw_variants)}개")

        # 상세 페이지 자체에서 랜딩 URL 추출 시도 (모든 variant 공통)
        page_landing_url = _extract_landing_url(page)
        if is_blocked_url(page_landing_url):
            page_landing_url = ""
        if page_landing_url:
            logger.info(f"  상세 페이지에서 랜딩 URL 추출: {page_landing_url[:80]}")

        # 각 대안별 랜딩 URL 결정
        for j, v in enumerate(raw_variants):
            content_url = v.get("content_url", "")
            landing_url = ""

            # 우선순위 1: sadbundle에서 adurl= 파싱
            if content_url and "sadbundle" in content_url:
                logger.info(f"  대안{j+1} sadbundle 방문 중...")
                landing_url = get_landing_from_sadbundle(page, content_url)
                if is_blocked_url(landing_url):
                    landing_url = ""
                # sadbundle 방문 후 상세 페이지로 복귀
                if landing_url:
                    try:
                        page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                    except Exception as e:
                        logger.warning(f"  대안{j+1} 상세 페이지 복귀 실패, skip: {e}")
                        continue
                    time.sleep(2)

            # 우선순위 2: variant의 anchor href (sub-container 내 <a> 태그)
            if not landing_url:
                anchor = v.get("anchor_href", "")
                if anchor and not is_blocked_url(anchor):
                    landing_url = anchor

            # 우선순위 3: 상세 페이지에서 추출한 공통 랜딩 URL
            if not landing_url:
                landing_url = page_landing_url

            if landing_url:
                logger.info(f"  대안{j+1} 랜딩 URL: {landing_url[:80]}")

            ad = variant_to_platform_ad(name, v, landing_url)
            ads.append(ad)

    return ads


def scrape_google_ads_by_keyword(
    keyword: str, headless: bool = True, max_results: int = 12, max_advertisers: int = 3
) -> list[PlatformAd]:
    three_months_ago = _THREE_MONTHS_AGO.strftime("%Y-%m-%d")
    today = date.today().strftime("%Y-%m-%d")

    logger.info(f"Google Ads Transparency 스크래핑 시작: keyword='{keyword}', max_advertisers={max_advertisers}, max_results={max_results}")

    base_url = (
        f"https://adstransparency.google.com/?region=KR"
        f"&start_date={three_months_ago}&end_date={today}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # 1. 광고주 목록 수집
        logger.info(f"광고주 목록 수집 중: keyword='{keyword}'")
        advertisers = _search_and_get_advertisers(page, keyword, base_url)
        if not advertisers:
            logger.warning(f"광고주 드롭다운 없음: keyword='{keyword}'")
            browser.close()
            return []

        advertisers_to_visit = advertisers[:max_advertisers]
        logger.info(f"광고주 {len(advertisers)}개 발견, {len(advertisers_to_visit)}개 순회 예정: {[a['name'] for a in advertisers_to_visit]}")

        # 2. 각 광고주 순회하며 광고 수집
        platform_ads: list[PlatformAd] = []
        seen_source_ids: set[str] = set()

        for adv_idx, adv in enumerate(advertisers_to_visit):
            remaining = max_results - len(platform_ads)
            if remaining <= 0:
                logger.info(f"max_results({max_results}) 도달, 순회 종료")
                break

            logger.info(f"=== 광고주 [{adv_idx+1}/{len(advertisers_to_visit)}] {adv['name']} (남은 수집 가능: {remaining}) ===")

            try:
                ads = _collect_ads_for_advertiser(
                    page, keyword, base_url,
                    advertiser_index=adv["index"],
                    advertiser_name=adv["name"],
                    max_creatives=remaining,
                )
            except Exception as e:
                logger.warning(f"광고주 '{adv['name']}' 수집 실패, skip: {e}")
                continue

            # 중복 제거 후 추가
            for ad in ads:
                if ad.source_id not in seen_source_ids:
                    seen_source_ids.add(ad.source_id)
                    platform_ads.append(ad)

                    if len(platform_ads) >= max_results:
                        logger.info(f"max_results({max_results}) 도달, 수집 종료")
                        break

            logger.info(f"광고주 '{adv['name']}' 완료: 이번 {len(ads)}건, 누적 {len(platform_ads)}건")

        logger.info(f"Google 스크래핑 완료: 총 {len(platform_ads)}건 (광고주 {len(advertisers_to_visit)}개 순회)")
        browser.close()

    return platform_ads


def scrape_google_ads_by_domain(
    domain: str,
    headless: bool = True,
    max_results: int | None = None,
    on_batch_callback: Callable[[list[PlatformAd]], None] | None = None,
    mode: str = "full",
) -> list[PlatformAd]:
    """도메인 기반 Google Ads Transparency 스크래핑.
    URL: https://adstransparency.google.com/?region=KR&domain={domain}

    max_results=None이면 전체 수집 (무제한 모드).
    on_batch_callback이 설정되면 50건마다 콜백 호출 후 메모리 해제.
    """
    # 방어적 도메인 정규화 (URL이 들어올 경우 대비)
    if "://" in domain:
        from urllib.parse import urlparse
        parsed = urlparse(domain)
        domain = parsed.netloc or parsed.path.rstrip("/")
    domain = domain.replace("www.", "").strip().rstrip("/")

    unlimited = max_results is None
    BATCH_SIZE = 50
    label = "unlimited" if unlimited else str(max_results)
    logger.info(f"Google Ads Transparency 도메인 스크래핑 시작: domain='{domain}', max_results={label}, mode={mode}")

    base_url = f"https://adstransparency.google.com/?region=KR&domain={domain}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # 1. 도메인 검색 페이지 접속
        logger.info(f"도메인 페이지 접속: {base_url}")
        page.goto(base_url, wait_until="load", timeout=60000)
        time.sleep(5)

        # 2. "See all ads" 확장 버튼 클릭 시도
        try:
            see_all_btn = page.locator("material-button.grid-expansion-button")
            if see_all_btn.count() > 0:
                see_all_btn.first.click()
                logger.info("'See all ads' 버튼 클릭 완료")
                time.sleep(3)
            else:
                logger.info("'See all ads' 버튼 없음 (모든 광고가 이미 표시된 상태)")
        except Exception as e:
            logger.warning(f"'See all ads' 버튼 클릭 실패: {e}")

        # 3. 스크롤하여 광고 카드 로드
        prev_count = 0
        scroll_attempts = 0
        no_new_count = 0  # 연속으로 새 광고가 없는 횟수
        max_scroll_attempts = 100 if unlimited else 15
        scroll_start_time = time.monotonic()
        SCROLL_TIMEOUT_SECONDS = 300  # 5분 안전 타임아웃

        while scroll_attempts < max_scroll_attempts:
            # 안전 타임아웃 체크
            elapsed = time.monotonic() - scroll_start_time
            if elapsed > SCROLL_TIMEOUT_SECONDS:
                logger.info(f"스크롤 타임아웃 ({SCROLL_TIMEOUT_SECONDS}초) 초과, 스크롤 중단")
                break

            current_count = page.evaluate(
                """() => document.querySelectorAll('creative-preview a[href*="/creative/"]').length"""
            )
            logger.info(f"스크롤 {scroll_attempts + 1}: 현재 {current_count}개 광고 발견 (경과: {elapsed:.0f}초)")

            if not unlimited and current_count >= max_results:
                logger.info(f"max_results({max_results}) 이상 로드됨, 스크롤 중단")
                break

            if current_count == prev_count:
                no_new_count += 1
                if no_new_count >= 3:
                    logger.info(f"연속 {no_new_count}회 스크롤에서 새 광고 없음, 스크롤 중단")
                    break
            else:
                no_new_count = 0

            prev_count = current_count
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            scroll_attempts += 1

        # 4. creative-preview 카드에서 상세 페이지 링크 수집
        ad_links = page.evaluate("""() => {
            const cards = document.querySelectorAll('creative-preview a');
            return Array.from(cards).map(a => a.getAttribute('href'))
                .filter(h => h && h.includes('/creative/'));
        }""")

        if not unlimited:
            ad_links = ad_links[:max_results]
        logger.info(f"크리에이티브 링크 {len(ad_links)}개 수집 (mode={'unlimited' if unlimited else f'max={max_results}'})")

        # 증분 모드: 이미 수집한 creative 건너뛰기
        skipped_count = 0
        if mode == "incremental":
            existing_ids = get_existing_creative_ids(domain)
            logger.info(f"증분 모드: DB에 {len(existing_ids)}개 기존 creative ID 발견")

            filtered_links = []
            for href in ad_links:
                cid = extract_creative_id_from_link(href)
                if cid and cid in existing_ids:
                    skipped_count += 1
                else:
                    filtered_links.append(href)

            logger.info(
                f"증분 필터: {len(ad_links)}개 중 {skipped_count}개 skip, "
                f"{len(filtered_links)}개 신규 상세 페이지 방문 예정"
            )
            ad_links = filtered_links

            if not ad_links:
                logger.info("증분 수집: 신규 광고 없음, 스크래핑 종료")
                browser.close()
                return []

        # 5. 각 상세 페이지 방문하여 광고 데이터 추출
        platform_ads: list[PlatformAd] = []
        seen_source_ids: set[str] = set()
        batch_buffer: list[PlatformAd] = []
        total_collected = 0

        for i, href in enumerate(ad_links):
            detail_url = f"https://adstransparency.google.com{href}"
            if "region=KR" not in detail_url:
                detail_url += ("&" if "?" in detail_url else "?") + "region=KR"

            logger.info(f"  [{i+1}/{len(ad_links)}] 상세 페이지: {href[:80]}")

            try:
                page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.warning(f"  [{i+1}/{len(ad_links)}] 상세 페이지 로드 실패, skip: {e}")
                continue
            time.sleep(3)

            # 광고주명
            name_el = page.query_selector("div.advertiser-name")
            advertiser_name = name_el.inner_text().strip() if name_el else domain

            # creative-details 패널 대기
            try:
                page.wait_for_selector("creative-details .ad-container", timeout=5000)
            except Exception:
                logger.warning(f"creative-details 패널 없음: url={detail_url[:100]}")
                continue

            # 실제 광고 콘텐츠 로드 대기
            try:
                page.wait_for_selector(
                    'creative-details img[src*="simgad"], '
                    'creative-details iframe[src*="youtube"], '
                    'creative-details iframe[src*="sadbundle"]',
                    timeout=5000,
                )
            except Exception:
                logger.debug("simgad/youtube/sadbundle 콘텐츠 미감지, 기존 DOM으로 진행")
            time.sleep(1)

            # 모든 대안 수집
            raw_variants = collect_all_variants(page)
            if not raw_variants:
                raw_variants = _collect_variants_from_frames(page)

            # 텍스트 광고 fallback: 이미지/영상 variant가 없지만 페이지에 텍스트 콘텐츠가 있는 경우
            if not raw_variants:
                is_text_format = page.evaluate("""() => {
                    const bodyText = document.body ? document.body.innerText : '';
                    return /형식\\s*[:\\uff1a]\\s*텍스트|Format\\s*[:\\uff1a]\\s*Text/i.test(bodyText);
                }""")
                if is_text_format:
                    ad_text = page.evaluate("""() => {
                        const container = document.querySelector('creative-details .ad-container');
                        return container ? container.innerText.trim() : '';
                    }""")
                    if ad_text:
                        raw_variants = [{
                            "content_url": "text_ad:" + hashlib.sha256(ad_text[:100].encode()).hexdigest()[:16],
                            "anchor_href": None,
                            "is_video": False,
                            "is_text": True,
                            "ad_copy_text": ad_text,
                            "video_url": None,
                            "thumbnail_url": None,
                            "youtube_video_id": None,
                        }]
                        logger.info(f"  텍스트 광고 감지: {ad_text[:80]}")

            logger.info(f"  {advertiser_name} | 대안 {len(raw_variants)}개")

            # 랜딩 URL 추출
            page_landing_url = _extract_landing_url(page)
            if is_blocked_url(page_landing_url):
                page_landing_url = ""
            if page_landing_url:
                logger.info(f"  상세 페이지에서 랜딩 URL 추출: {page_landing_url[:80]}")

            # 각 대안별 PlatformAd 생성
            hit_limit = False
            for j, v in enumerate(raw_variants):
                content_url = v.get("content_url", "")
                landing_url = ""

                # 우선순위 1: sadbundle에서 adurl= 파싱
                if content_url and "sadbundle" in content_url:
                    logger.info(f"  대안{j+1} sadbundle 방문 중...")
                    landing_url = get_landing_from_sadbundle(page, content_url)
                    if is_blocked_url(landing_url):
                        landing_url = ""
                    if landing_url:
                        try:
                            page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                        except Exception as e:
                            logger.warning(f"  대안{j+1} 상세 페이지 복귀 실패, skip: {e}")
                            continue
                        time.sleep(2)

                # 우선순위 2: variant의 anchor href
                if not landing_url:
                    anchor = v.get("anchor_href", "")
                    if anchor and not is_blocked_url(anchor):
                        landing_url = anchor

                # 우선순위 3: 상세 페이지 공통 랜딩 URL
                if not landing_url:
                    landing_url = page_landing_url

                if landing_url:
                    logger.info(f"  대안{j+1} 랜딩 URL: {landing_url[:80]}")

                ad = variant_to_platform_ad(advertiser_name, v, landing_url)

                # creative_id 설정
                cid = extract_creative_id_from_link(href)
                if cid:
                    ad.creative_id = cid

                if ad.source_id not in seen_source_ids:
                    seen_source_ids.add(ad.source_id)
                    total_collected += 1

                    if on_batch_callback is not None:
                        batch_buffer.append(ad)
                        if len(batch_buffer) >= BATCH_SIZE:
                            logger.info(f"  배치 콜백: {len(batch_buffer)}건 전달 (누적 {total_collected}건)")
                            on_batch_callback(batch_buffer)
                            batch_buffer = []
                    else:
                        platform_ads.append(ad)

                    if not unlimited and total_collected >= max_results:
                        logger.info(f"max_results({max_results}) 도달, 수집 종료")
                        hit_limit = True
                        break

            if hit_limit:
                break

        # 남은 배치 처리
        if on_batch_callback is not None and batch_buffer:
            logger.info(f"  최종 배치 콜백: {len(batch_buffer)}건 전달 (누적 {total_collected}건)")
            on_batch_callback(batch_buffer)
            batch_buffer = []

        logger.info(f"Google 도메인 스크래핑 완료: 총 {total_collected}건 (domain='{domain}')")
        browser.close()

    # on_batch_callback이 있으면 이미 콜백으로 전달했으므로 빈 리스트 반환
    if on_batch_callback is not None:
        return []
    return platform_ads


def main(keyword: str = "", domain: str = "", headless: bool = True, max_results: int = 12, max_advertisers: int = 3, no_limit: bool = False) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if domain:
        effective_max = None if no_limit else max_results
        platform_ads = scrape_google_ads_by_domain(
            domain, headless=headless, max_results=effective_max
        )
        return {
            "domain": domain,
            "source": "google_ads_transparency",
            "search_type": "domain",
            "mode": "unlimited" if no_limit else f"max={max_results}",
            "scraped_at": datetime.now().isoformat(),
            "total_count": len(platform_ads),
            "ads": [ad.model_dump(mode="json") for ad in platform_ads],
        }

    platform_ads = scrape_google_ads_by_keyword(
        keyword, headless=headless, max_results=max_results, max_advertisers=max_advertisers
    )
    return {
        "keyword": keyword,
        "source": "google_ads_transparency",
        "search_type": "keyword",
        "scraped_at": datetime.now().isoformat(),
        "total_count": len(platform_ads),
        "ads": [ad.model_dump(mode="json") for ad in platform_ads],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Ads Transparency Scraper (PlatformAd)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--keyword", type=str, help="Search by keyword")
    group.add_argument("--domain", type=str, help="Search by domain (e.g. i-hi.co.kr)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode")
    parser.add_argument("--max-results", type=int, default=12, help="Maximum total number of ads to collect")
    parser.add_argument("--max-advertisers", type=int, default=3, help="Maximum number of advertisers to visit (keyword mode only)")
    parser.add_argument("--no-limit", action="store_true", default=False, help="도메인의 모든 광고 수집 (max_results 무시)")
    args = parser.parse_args()

    result = main(
        keyword=args.keyword or "",
        domain=args.domain or "",
        headless=args.headless,
        max_results=args.max_results,
        max_advertisers=args.max_advertisers,
        no_limit=args.no_limit,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"google_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
