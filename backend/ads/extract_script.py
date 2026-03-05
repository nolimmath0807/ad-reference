import logging
import os
import subprocess
import tempfile

import httpx
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from conn import get_db

load_dotenv()

logger = logging.getLogger("extract_script")


def extract_script(ad_id: str) -> dict:
    """광고 영상에서 원고를 추출하여 DB에 저장."""

    with get_db() as (conn, cur):
        # 광고 조회
        cur.execute("SELECT preview_url, media_type FROM ads WHERE id = %s", (ad_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Ad not found: {ad_id}")

        preview_url, media_type = row
        if media_type != "video":
            raise ValueError(f"Not a video ad (media_type={media_type})")
        if not preview_url:
            raise ValueError("No preview_url for this ad")

        # 이미 처리 중이면 중복 방지
        cur.execute("SELECT status, script_text FROM ad_scripts WHERE ad_id = %s", (ad_id,))
        existing = cur.fetchone()
        if existing and existing[0] == "processing":
            return {"ad_id": ad_id, "status": "processing", "script_text": None}

        # processing 상태로 upsert
        if existing:
            cur.execute(
                "UPDATE ad_scripts SET status = 'processing', error_message = NULL, updated_at = NOW() WHERE ad_id = %s",
                (ad_id,),
            )
        else:
            cur.execute(
                "INSERT INTO ad_scripts (ad_id, status) VALUES (%s, 'processing')",
                (ad_id,),
            )

    # 실제 추출 (DB 트랜잭션 밖)
    try:
        script_text = _download_and_transcribe(preview_url)

        with get_db() as (conn, cur):
            cur.execute(
                "UPDATE ad_scripts SET script_text = %s, status = 'completed', updated_at = NOW() WHERE ad_id = %s",
                (script_text, ad_id),
            )

        return {"ad_id": ad_id, "status": "completed", "script_text": script_text}

    except Exception as e:
        logger.error(f"Script extraction failed for ad {ad_id}: {e}")
        with get_db() as (conn, cur):
            cur.execute(
                "UPDATE ad_scripts SET status = 'failed', error_message = %s, updated_at = NOW() WHERE ad_id = %s",
                (str(e)[:500], ad_id),
            )
        return {"ad_id": ad_id, "status": "failed", "error_message": str(e)}


def _is_youtube_url(url: str) -> bool:
    return any(host in url for host in ["youtube.com", "youtu.be"])


def _download_youtube(url: str, output_path: str):
    import yt_dlp

    ydl_opts = {
        "format": "worst[ext=mp4]/worst",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    if not os.path.exists(output_path):
        raise RuntimeError(f"yt-dlp failed to download: {url}")


def _download_direct(url: str, output_path: str):
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


def _download_and_transcribe(video_url: str) -> str:
    """영상 다운로드 -> ffmpeg 오디오 추출 -> Whisper STT"""

    with tempfile.TemporaryDirectory() as tmp_dir:
        video_path = os.path.join(tmp_dir, "video.mp4")
        audio_path = os.path.join(tmp_dir, "audio.wav")

        # YouTube URL이면 yt-dlp, 그 외면 httpx 직접 다운로드
        if _is_youtube_url(video_url):
            _download_youtube(video_url, video_path)
        else:
            _download_direct(video_url, video_path)

        # ffmpeg 오디오 추출
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", audio_path, "-y"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[:300]}")

        # Whisper STT
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            raise RuntimeError("HF_TOKEN not configured")

        client = InferenceClient(provider="auto", api_key=hf_token)
        output = client.automatic_speech_recognition(
            audio_path, model="openai/whisper-large-v3-turbo"
        )

        return output.text


def get_script(ad_id: str) -> dict | None:
    """저장된 원고를 조회."""
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT ad_id, script_text, status, error_message FROM ad_scripts WHERE ad_id = %s",
            (ad_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "ad_id": str(row[0]),
            "script_text": row[1],
            "status": row[2],
            "error_message": row[3],
        }
