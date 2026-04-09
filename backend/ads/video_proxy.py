import logging
import os

import httpx

from conn import get_db
from ads.extract_script import _is_youtube_url

logger = logging.getLogger("video_proxy")

CACHE_DIR = "/tmp/ad-videos"


def get_video_path(ad_id: str) -> str | None:
    """영상을 캐시하여 로컬 파일 경로를 반환한다.

    - 캐시에 이미 있으면 바로 반환
    - DB에서 preview_url 조회 후:
      - YouTube URL이면 yt-dlp로 다운로드
      - 비유튜브 URL이면 httpx로 직접 다운로드
    - 다운로드 실패시 None 반환
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{ad_id}.mp4")

    # 캐시 히트
    if os.path.exists(cache_path):
        logger.info("Cache hit for ad %s", ad_id)
        return cache_path

    # DB에서 preview_url 조회
    with get_db() as (conn, cur):
        cur.execute("SELECT preview_url FROM ads WHERE id = %s", (ad_id,))
        row = cur.fetchone()

    if not row or not row[0]:
        return None

    preview_url = row[0]

    if _is_youtube_url(preview_url):
        # yt-dlp로 다운로드
        logger.info("Downloading YouTube video for ad %s: %s", ad_id, preview_url)
        import yt_dlp

        ydl_opts = {
            "format": "worst[ext=mp4]/worst",
            "outtmpl": cache_path,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([preview_url])
        except Exception:
            logger.exception("yt-dlp download failed for ad %s (url=%s)", ad_id, preview_url)
            return None

        if not os.path.exists(cache_path):
            logger.error("yt-dlp produced no output file for ad %s (url=%s)", ad_id, preview_url)
            return None
    else:
        # httpx로 직접 다운로드 (비유튜브 CDN URL)
        logger.info("Downloading non-YouTube video for ad %s: %s", ad_id, preview_url)
        try:
            with httpx.stream("GET", preview_url, follow_redirects=True, timeout=60) as r:
                if r.status_code != 200:
                    logger.warning(
                        "Non-200 response (%s) for ad %s (url=%s)", r.status_code, ad_id, preview_url
                    )
                    return None
                with open(cache_path, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        except Exception:
            logger.exception("httpx download failed for ad %s (url=%s)", ad_id, preview_url)
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return None

        if not os.path.exists(cache_path):
            logger.error("httpx produced no output file for ad %s (url=%s)", ad_id, preview_url)
            return None

    logger.info("Cached video for ad %s at %s", ad_id, cache_path)
    return cache_path


def get_preview_url(ad_id: str) -> str | None:
    """DB에서 preview_url을 조회하여 반환한다."""
    with get_db() as (conn, cur):
        cur.execute("SELECT preview_url FROM ads WHERE id = %s", (ad_id,))
        row = cur.fetchone()

    if not row or not row[0]:
        return None
    return row[0]
