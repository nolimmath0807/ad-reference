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
        from botocore.config import Config

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=_REGION,
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": 2},
            ),
        )
    return _s3_client


_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
_DOWNLOAD_TIMEOUT = 60  # seconds


def upload_from_url(url: str, s3_key_prefix: str, cookies: dict[str, str] | None = None) -> str | None:
    """
    URL에서 미디어를 다운로드하여 S3에 업로드하고 퍼블릭 URL 반환.
    실패 시 None 반환 (원본 URL 유지하도록).

    안전장치:
    - HEAD 요청으로 Content-Length 사전 확인 (50MB 초과 스킵)
    - 스트리밍 다운로드로 메모리 절약 + 누적 사이즈 체크
    - 전체 timeout 60초 제한
    """
    if not url or not url.startswith("http"):
        return None

    if not is_s3_configured():
        logger.warning("S3 미설정 (AWS_ACCESS_KEY_ID 없음), 업로드 건너뜀")
        return None

    content_type = ""

    # Step 1: HEAD 요청으로 사이즈 사전 확인
    try:
        head_resp = httpx.head(url, timeout=10, follow_redirects=True, cookies=cookies)
        head_resp.raise_for_status()
        content_length = int(head_resp.headers.get("content-length", "0"))
        content_type = head_resp.headers.get("content-type", "").split(";")[0].strip()
        if content_length > _MAX_FILE_SIZE:
            logger.error(
                f"파일 크기 초과 스킵: {content_length:,} bytes > {_MAX_FILE_SIZE:,}, url={url[:100]}"
            )
            return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 405:
            logger.debug(f"HEAD 미지원 (405), GET으로 fallback: url={url[:100]}")
        else:
            logger.error(f"HEAD 요청 HTTP 에러: status={e.response.status_code}, url={url[:100]}")
            return None
    except Exception as e:
        logger.debug(f"HEAD 요청 실패 (GET으로 fallback): {type(e).__name__}: {e}")

    # Step 2: 스트리밍 다운로드 (청크별 사이즈 체크)
    chunks = []
    downloaded_size = 0

    try:
        with httpx.stream(
            "GET", url, timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True, cookies=cookies
        ) as response:
            response.raise_for_status()

            if not content_type:
                content_type = response.headers.get("content-type", "").split(";")[0].strip()

            # GET 응답의 Content-Length도 체크 (HEAD 실패 시 fallback)
            get_content_length = int(response.headers.get("content-length", "0"))
            if get_content_length > _MAX_FILE_SIZE:
                logger.error(
                    f"파일 크기 초과 스킵 (GET Content-Length): {get_content_length:,} bytes > {_MAX_FILE_SIZE:,}, url={url[:100]}"
                )
                return None

            for chunk in response.iter_bytes(chunk_size=1024 * 64):
                downloaded_size += len(chunk)
                if downloaded_size > _MAX_FILE_SIZE:
                    logger.error(
                        f"다운로드 중 크기 초과 중단 (스트리밍): {downloaded_size:,} bytes > {_MAX_FILE_SIZE:,}, url={url[:100]}"
                    )
                    return None
                chunks.append(chunk)
    except httpx.HTTPStatusError as e:
        logger.error(f"다운로드 HTTP 에러: status={e.response.status_code}, url={url[:100]}")
        return None
    except Exception as e:
        logger.error(f"다운로드 실패: url={url[:100]}, error={type(e).__name__}: {e}")
        return None

    body = b"".join(chunks)
    file_size = len(body)

    # Step 3: 확장자 결정
    ext = mimetypes.guess_extension(content_type) if content_type else None

    if not ext:
        path = urlparse(url).path
        dot_idx = path.rfind(".")
        ext = path[dot_idx:] if dot_idx != -1 else ".bin"

    if ext == ".jpe":
        ext = ".jpg"

    # Step 4: S3 업로드
    s3_key = f"{s3_key_prefix}/{uuid.uuid4().hex}{ext}"

    try:
        _get_s3_client().put_object(
            Bucket=_BUCKET,
            Key=s3_key,
            Body=body,
            ContentType=content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.error(f"S3 업로드 실패: key={s3_key}, size={file_size}, error={type(e).__name__}: {e}")
        return None

    public_url = f"https://{_BUCKET}.s3.{_REGION}.amazonaws.com/{s3_key}"
    logger.info(f"S3 업로드 성공: {public_url} ({file_size:,} bytes)")
    return public_url


def upload_from_file(local_path: str, s3_key: str, content_type: str = "video/mp4") -> str | None:
    """
    로컬 파일을 S3에 업로드하고 퍼블릭 URL 반환.
    실패 시 None 반환.
    """
    if not is_s3_configured():
        logger.warning("S3 미설정, 업로드 건너뜀")
        return None
    try:
        with open(local_path, "rb") as f:
            _get_s3_client().put_object(
                Bucket=_BUCKET,
                Key=s3_key,
                Body=f,
                ContentType=content_type,
            )
        public_url = f"https://{_BUCKET}.s3.{_REGION}.amazonaws.com/{s3_key}"
        file_size = os.path.getsize(local_path)
        logger.info(f"S3 파일 업로드 성공: {public_url} ({file_size:,} bytes)")
        return public_url
    except Exception as e:
        logger.error(f"S3 파일 업로드 실패: key={s3_key}, error={type(e).__name__}: {e}")
        return None


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
