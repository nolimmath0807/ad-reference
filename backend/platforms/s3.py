import argparse
import json
import logging
import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("s3")

_s3_client = None
_BUCKET = os.getenv("AWS_S3_BUCKET", "ad-reference-media")
_REGION = os.getenv("AWS_REGION", "ap-northeast-2")


def is_s3_configured() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID"))


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=_REGION,
        )
    return _s3_client


def upload_from_url(url: str, s3_key_prefix: str) -> str | None:
    """
    URL에서 미디어를 다운로드하여 S3에 업로드하고 퍼블릭 URL 반환.
    실패 시 None 반환 (원본 URL 유지하도록).
    """
    if not url or not url.startswith("http"):
        return None

    if not is_s3_configured():
        logger.warning("S3 미설정 (AWS_ACCESS_KEY_ID 없음), 업로드 건너뜀")
        return None

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"다운로드 HTTP 에러: status={e.response.status_code}, url={url[:100]}")
        return None
    except Exception as e:
        logger.error(f"다운로드 실패: url={url[:100]}, error={type(e).__name__}: {e}")
        return None

    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    ext = mimetypes.guess_extension(content_type) if content_type else None

    if not ext:
        path = urlparse(url).path
        dot_idx = path.rfind(".")
        ext = path[dot_idx:] if dot_idx != -1 else ".bin"

    if ext == ".jpe":
        ext = ".jpg"

    s3_key = f"{s3_key_prefix}/{uuid.uuid4().hex}{ext}"
    file_size = len(response.content)

    try:
        _get_s3_client().put_object(
            Bucket=_BUCKET,
            Key=s3_key,
            Body=response.content,
            ContentType=content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.error(f"S3 업로드 실패: key={s3_key}, size={file_size}, error={type(e).__name__}: {e}")
        return None

    public_url = f"https://{_BUCKET}.s3.{_REGION}.amazonaws.com/{s3_key}"
    logger.info(f"S3 업로드 성공: {public_url} ({file_size:,} bytes)")
    return public_url


def main(url: str, prefix: str) -> dict:
    logging.basicConfig(level=logging.INFO)

    logger.info(f"S3 설정 여부: {is_s3_configured()}")
    result_url = upload_from_url(url, prefix)

    return {
        "original_url": url,
        "s3_url": result_url,
        "s3_configured": is_s3_configured(),
        "bucket": _BUCKET,
        "region": _REGION,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S3 미디어 업로드 테스트")
    parser.add_argument("--url", required=True, help="테스트할 이미지 URL")
    parser.add_argument("--prefix", default="test", help="S3 key prefix")
    args = parser.parse_args()

    result = main(args.url, args.prefix)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"s3_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
