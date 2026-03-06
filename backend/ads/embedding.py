import logging
import os
import time

import numpy as np
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from conn import get_db

load_dotenv()

logger = logging.getLogger("embedding")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _get_hf_client() -> InferenceClient:
    """HuggingFace InferenceClient 생성."""
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN not configured")
    return InferenceClient(api_key=hf_token)


def _flatten_embedding(raw) -> list[float]:
    """HF API 반환값을 1D list[float]로 변환.

    feature_extraction 결과가 nested list일 수 있으므로
    numpy로 flatten 후 list로 변환한다.
    """
    arr = np.array(raw, dtype=np.float32).flatten()
    # all-MiniLM-L6-v2는 384차원이므로, 더 긴 경우 앞 384개만 사용
    if len(arr) > 384:
        arr = arr[:384]
    return arr.tolist()


def generate_image_embedding(image_url: str) -> list[float] | None:
    """이미지 URL -> 이미지 임베딩. 향후 이미지 임베딩 추가 예정."""
    # TODO: 향후 이미지 임베딩 모델 연동 시 구현
    return None


def generate_text_embedding(text: str) -> list[float] | None:
    """텍스트 -> 텍스트 임베딩 (384차원)."""
    if not text or not text.strip():
        return None

    # 약 200자로 truncate
    truncated = text.strip()[:200]

    try:
        client = _get_hf_client()
        raw = client.feature_extraction(truncated, model=EMBEDDING_MODEL)
        return _flatten_embedding(raw)
    except Exception as e:
        logger.warning(f"Text embedding failed: {e}")
        return None


def combine_embeddings(
    image_emb: list[float] | None,
    text_emb: list[float] | None,
    image_weight: float = 0.7,
) -> list[float] | None:
    """임베딩 결합. 현재는 텍스트 임베딩만 사용."""
    if text_emb is not None:
        return text_emb
    return image_emb


def _vector_to_pgvector(vec: list[float]) -> str:
    """list[float] -> pgvector 문자열 포맷 '[1.0,2.0,...]'."""
    return "[" + ",".join(str(v) for v in vec) + "]"


def embed_ad(ad_id: str) -> dict:
    """단일 광고 임베딩 생성 및 DB 저장."""
    # 1. ads 테이블에서 ad_copy, advertiser_name, cta_text 조회
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT ad_copy, advertiser_name, cta_text FROM ads WHERE id = %s",
            (ad_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"ad_id": ad_id, "status": "failed", "error": "Ad not found"}

        ad_copy, advertiser_name, cta_text = row

    # 2. 임베딩용 텍스트 구성: ad_copy 우선, 없으면 다른 필드 조합
    embed_text = ad_copy
    if not embed_text or not embed_text.strip():
        fallback_parts = [advertiser_name or "", cta_text or ""]
        embed_text = " ".join(p for p in fallback_parts if p.strip())

    # 3. 임베딩 생성 (DB 트랜잭션 밖에서)
    try:
        text_emb = generate_text_embedding(embed_text)
        combined_emb = combine_embeddings(None, text_emb)

        if combined_emb is None:
            raise ValueError("Text embedding failed")

        # 4. ad_embeddings 테이블에 UPSERT
        with get_db() as (conn, cur):
            text_pg = _vector_to_pgvector(text_emb) if text_emb else None
            combined_pg = _vector_to_pgvector(combined_emb)

            cur.execute(
                """
                INSERT INTO ad_embeddings (ad_id, text_embedding, combined_embedding, status, model_name)
                VALUES (%s, %s::vector, %s::vector, 'completed', %s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    text_embedding = EXCLUDED.text_embedding,
                    combined_embedding = EXCLUDED.combined_embedding,
                    status = 'completed',
                    error_message = NULL,
                    updated_at = NOW()
                """,
                (ad_id, text_pg, combined_pg, EMBEDDING_MODEL),
            )

        logger.info(f"Embedding completed for ad {ad_id}")
        return {
            "ad_id": ad_id,
            "status": "completed",
            "has_text_embedding": text_emb is not None,
        }

    except Exception as e:
        logger.error(f"Embedding failed for ad {ad_id}: {e}")
        with get_db() as (conn, cur):
            cur.execute(
                """
                INSERT INTO ad_embeddings (ad_id, status, error_message)
                VALUES (%s, 'failed', %s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    status = 'failed',
                    error_message = EXCLUDED.error_message,
                    updated_at = NOW()
                """,
                (ad_id, str(e)[:500]),
            )
        return {"ad_id": ad_id, "status": "failed", "error": str(e)}


def find_similar_ads(
    ad_id: str, limit: int = 6, min_similarity: float = 0.3
) -> list[dict]:
    """벡터 유사도 기반으로 유사 광고 조회."""
    with get_db() as (conn, cur):
        # 1. target ad의 text_embedding 조회
        cur.execute(
            "SELECT text_embedding::text FROM ad_embeddings WHERE ad_id = %s AND status = 'completed'",
            (ad_id,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return []

        target_embedding = row[0]

        # 2. 코사인 거리로 유사 광고 검색
        cur.execute(
            """
            SELECT a.id, a.platform, a.format, a.advertiser_name,
                   a.thumbnail_url, a.preview_url, a.media_type,
                   a.ad_copy, a.cta_text, a.landing_page_url,
                   1 - (e.text_embedding <=> %s::vector) AS similarity
            FROM ads a
            JOIN ad_embeddings e ON a.id = e.ad_id
            WHERE a.id != %s
              AND e.status = 'completed'
              AND e.text_embedding IS NOT NULL
            ORDER BY e.text_embedding <=> %s::vector
            LIMIT %s
            """,
            (target_embedding, ad_id, target_embedding, limit),
        )

        results = []
        for r in cur.fetchall():
            similarity = float(r[10])
            if similarity < min_similarity:
                continue
            results.append({
                "id": str(r[0]),
                "platform": r[1],
                "format": r[2],
                "advertiser_name": r[3],
                "thumbnail_url": r[4],
                "preview_url": r[5],
                "media_type": r[6],
                "ad_copy": r[7],
                "cta_text": r[8],
                "landing_page_url": r[9],
                "similarity": round(similarity, 4),
            })

        return results


def embed_ads_batch(limit: int = 100) -> dict:
    """임베딩이 없는 광고들을 배치 처리."""
    # 1. 임베딩이 없거나 completed가 아닌 광고 조회
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT a.id FROM ads a
            LEFT JOIN ad_embeddings e ON a.id = e.ad_id
            WHERE e.ad_id IS NULL OR e.status != 'completed'
            ORDER BY a.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        ad_ids = [str(row[0]) for row in cur.fetchall()]

    succeeded = 0
    failed = 0

    for ad_id in ad_ids:
        result = embed_ad(ad_id)
        if result["status"] == "completed":
            succeeded += 1
        else:
            failed += 1

        # rate limit 대응
        time.sleep(1.0)

    summary = {
        "processed": len(ad_ids),
        "succeeded": succeeded,
        "failed": failed,
    }
    logger.info(f"Batch embedding complete: {summary}")
    return summary
