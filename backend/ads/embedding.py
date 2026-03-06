import logging
import os
import io
import time
from functools import lru_cache

import httpx
import numpy as np
from dotenv import load_dotenv

from conn import get_db

load_dotenv()
logger = logging.getLogger("embedding")

CLIP_MODEL_NAME = "clip-ViT-B-32"
EMBEDDING_DIM = 512


@lru_cache(maxsize=1)
def _get_model():
    """CLIP 모델 로드 (싱글턴, 최초 1회만 로드)."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading CLIP model: {CLIP_MODEL_NAME}")
    model = SentenceTransformer(CLIP_MODEL_NAME)
    return model


def generate_image_embedding(image_url: str) -> list[float] | None:
    """이미지 URL -> CLIP 이미지 임베딩 (512차원)."""
    try:
        from PIL import Image
        resp = httpx.get(image_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        model = _get_model()
        embedding = model.encode(img)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Image embedding failed for {image_url}: {e}")
        return None


def generate_text_embedding(text: str) -> list[float] | None:
    """텍스트 -> CLIP 텍스트 임베딩 (512차원)."""
    if not text or not text.strip():
        return None
    truncated = text.strip()[:200]
    try:
        model = _get_model()
        embedding = model.encode(truncated)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Text embedding failed: {e}")
        return None


def combine_embeddings(
    image_emb: list[float] | None,
    text_emb: list[float] | None,
    image_weight: float = 0.7,
) -> list[float] | None:
    """이미지 + 텍스트 임베딩 가중 평균, L2 정규화."""
    if image_emb is None and text_emb is None:
        return None
    if image_emb is None:
        return text_emb
    if text_emb is None:
        return image_emb

    img_arr = np.array(image_emb, dtype=np.float32)
    txt_arr = np.array(text_emb, dtype=np.float32)
    combined = image_weight * img_arr + (1 - image_weight) * txt_arr
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm
    return combined.tolist()


def _vector_to_pgvector(vec: list[float]) -> str:
    """list[float] -> pgvector 문자열 포맷."""
    return "[" + ",".join(str(v) for v in vec) + "]"


def embed_ad(ad_id: str) -> dict:
    """단일 광고 임베딩 생성 및 DB 저장."""
    with get_db() as (conn, cur):
        cur.execute("SELECT thumbnail_url, ad_copy, advertiser_name, cta_text FROM ads WHERE id = %s", (ad_id,))
        row = cur.fetchone()
        if not row:
            return {"ad_id": ad_id, "status": "failed", "error": "Ad not found"}
        thumbnail_url, ad_copy, advertiser_name, cta_text = row

    # 이미지 임베딩
    image_emb = generate_image_embedding(thumbnail_url) if thumbnail_url else None

    # 텍스트 임베딩 (ad_copy 없으면 advertiser_name + cta_text 조합)
    text = ad_copy or f"{advertiser_name or ''} {cta_text or ''}".strip()
    text_emb = generate_text_embedding(text) if text else None

    # 결합
    combined_emb = combine_embeddings(image_emb, text_emb)

    if combined_emb is None and image_emb is None and text_emb is None:
        with get_db() as (conn, cur):
            cur.execute(
                "INSERT INTO ad_embeddings (ad_id, status, error_message, model_name) VALUES (%s, 'failed', %s, %s) ON CONFLICT (ad_id) DO UPDATE SET status = 'failed', error_message = EXCLUDED.error_message, updated_at = NOW()",
                (ad_id, "No embeddable content", CLIP_MODEL_NAME),
            )
        return {"ad_id": ad_id, "status": "failed", "error": "No embeddable content"}

    try:
        with get_db() as (conn, cur):
            img_vec = _vector_to_pgvector(image_emb) if image_emb else None
            txt_vec = _vector_to_pgvector(text_emb) if text_emb else None
            comb_vec = _vector_to_pgvector(combined_emb) if combined_emb else None

            cur.execute("""
                INSERT INTO ad_embeddings (ad_id, image_embedding, text_embedding, combined_embedding, status, model_name)
                VALUES (%s, %s::vector, %s::vector, %s::vector, 'completed', %s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    image_embedding = EXCLUDED.image_embedding,
                    text_embedding = EXCLUDED.text_embedding,
                    combined_embedding = EXCLUDED.combined_embedding,
                    status = 'completed',
                    error_message = NULL,
                    model_name = EXCLUDED.model_name,
                    updated_at = NOW()
            """, (ad_id, img_vec, txt_vec, comb_vec, CLIP_MODEL_NAME))

        logger.info(f"Embedding completed for ad {ad_id} (img={'Y' if image_emb else 'N'}, txt={'Y' if text_emb else 'N'})")
        return {"ad_id": ad_id, "status": "completed"}
    except Exception as e:
        logger.error(f"Embedding failed for ad {ad_id}: {e}")
        with get_db() as (conn, cur):
            cur.execute(
                "INSERT INTO ad_embeddings (ad_id, status, error_message, model_name) VALUES (%s, 'failed', %s, %s) ON CONFLICT (ad_id) DO UPDATE SET status = 'failed', error_message = EXCLUDED.error_message, updated_at = NOW()",
                (ad_id, str(e)[:500], CLIP_MODEL_NAME),
            )
        return {"ad_id": ad_id, "status": "failed", "error": str(e)}


def find_similar_ads(ad_id: str, limit: int = 6, min_similarity: float = 0.3) -> list[dict]:
    """벡터 유사도로 유사 광고 조회. combined_embedding 사용."""
    with get_db() as (conn, cur):
        cur.execute("SELECT combined_embedding FROM ad_embeddings WHERE ad_id = %s AND status = 'completed'", (ad_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return []
        target_vec = row[0]

        cur.execute("""
            SELECT a.*, 1 - (e.combined_embedding <=> %s::vector) AS similarity
            FROM ads a
            JOIN ad_embeddings e ON a.id = e.ad_id
            WHERE a.id != %s
              AND e.status = 'completed'
              AND e.combined_embedding IS NOT NULL
            ORDER BY e.combined_embedding <=> %s::vector
            LIMIT %s
        """, (target_vec, ad_id, target_vec, limit))

        columns = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))
        return results


def embed_ads_batch(limit: int = 100) -> dict:
    """배치 임베딩 (embed_ad를 반복 호출)."""
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT a.id FROM ads a
            LEFT JOIN ad_embeddings e ON a.id = e.ad_id AND e.status = 'completed'
            WHERE e.id IS NULL
            ORDER BY a.created_at DESC
            LIMIT %s
        """, (limit,))
        ad_ids = [str(row[0]) for row in cur.fetchall()]

    succeeded = 0
    failed = 0
    for ad_id in ad_ids:
        result = embed_ad(ad_id)
        if result.get("status") == "completed":
            succeeded += 1
        else:
            failed += 1
        time.sleep(0.1)  # 로컬 실행이므로 rate limit 짧게

    summary = {
        "processed": len(ad_ids),
        "succeeded": succeeded,
        "failed": failed,
    }
    logger.info(f"Batch embedding complete: {summary}")
    return summary


def search_ads_by_vector(query_text: str, limit: int = 20, min_similarity: float = 0.15) -> list[dict]:
    """텍스트 쿼리 -> CLIP 텍스트 임베딩 -> 벡터 유사도 검색."""
    text_emb = generate_text_embedding(query_text)
    if text_emb is None:
        return []

    vec_str = _vector_to_pgvector(text_emb)

    with get_db() as (conn, cur):
        cur.execute("""
            SELECT a.id, a.platform, a.format, a.advertiser_name, a.advertiser_handle,
                   a.advertiser_avatar_url, a.thumbnail_url, a.preview_url, a.media_type,
                   a.ad_copy, a.cta_text, a.likes, a.comments, a.shares,
                   a.start_date, a.end_date, a.tags, a.landing_page_url,
                   a.created_at, a.saved_at,
                   1 - (e.combined_embedding <=> %s::vector) AS similarity
            FROM ads a
            JOIN ad_embeddings e ON a.id = e.ad_id
            WHERE e.status = 'completed'
              AND e.combined_embedding IS NOT NULL
              AND a.thumbnail_url != ''
              AND a.thumbnail_url NOT LIKE '%%html%%'
            ORDER BY e.combined_embedding <=> %s::vector
            LIMIT %s
        """, (vec_str, vec_str, limit))

        columns = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            d = dict(zip(columns, row))
            if d.get("similarity", 0) >= min_similarity:
                results.append(d)
        return results
