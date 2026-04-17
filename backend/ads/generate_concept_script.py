import argparse
import json
import os
import random
from datetime import datetime
from pathlib import Path

from google import genai
import httpx
from dotenv import load_dotenv

from conn import get_db

load_dotenv()


def fetch_ref_scripts(ref_count: int, advertiser: str | None) -> list[dict]:
    with get_db() as (conn, cur):
        if advertiser:
            cur.execute(
                """
                SELECT s.script_text, a.advertiser_name
                FROM ad_scripts s
                JOIN ads a ON a.id = s.ad_id
                WHERE s.status = 'completed'
                  AND a.advertiser_name ILIKE %s
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (f"%{advertiser}%", ref_count),
            )
        else:
            cur.execute(
                """
                SELECT s.script_text, a.advertiser_name
                FROM ad_scripts s
                JOIN ads a ON a.id = s.ad_id
                WHERE s.status = 'completed'
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (ref_count,),
            )
        rows = cur.fetchall()
    return [{"script_text": row[0], "advertiser_name": row[1]} for row in rows]


def fetch_product_from_db(slug: str, selling_point_label: str) -> dict:
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, name, form, dosage, cta_channel, videofactory_product_id
            FROM ad_reference_dash.products
            WHERE slug = %s
            """,
            (slug,),
        )
        product_row = cur.fetchone()
        if product_row is None:
            raise ValueError(f"상품을 찾을 수 없습니다: slug={slug}")
        product_id_db, name, form, dosage, cta_channel, videofactory_product_id = product_row

        cur.execute(
            """
            SELECT headline, mechanism, key_ingredients, target_symptoms, competitor_alt
            FROM ad_reference_dash.product_selling_points
            WHERE product_id = %s AND label = %s AND is_active = TRUE
            """,
            (str(product_id_db), selling_point_label),
        )
        sp_row = cur.fetchone()
        if sp_row is None:
            raise ValueError(f"소구점을 찾을 수 없습니다: slug={slug}, label={selling_point_label}")
        headline, mechanism, key_ingredients, target_symptoms, competitor_alt = sp_row

        cur.execute(
            """
            SELECT asset_label
            FROM ad_reference_dash.product_assets
            WHERE product_id = %s
            ORDER BY asset_key
            """,
            (str(product_id_db),),
        )
        asset_rows = cur.fetchall()
        asset_labels = ", ".join(row[0] for row in asset_rows if row[0])

        cur.execute(
            """
            SELECT option_name, price, discount_rate, daily_price
            FROM ad_reference_dash.product_pricing
            WHERE product_id = %s AND is_main = TRUE
            LIMIT 1
            """,
            (str(product_id_db),),
        )
        pricing_row = cur.fetchone()

    pricing_str = ""
    if pricing_row:
        option_name, price, discount_rate, daily_price = pricing_row
        pricing_str = f"{option_name} {price:,}원 (할인율 {discount_rate}%, 하루 {daily_price}원)"

    symptoms_str = ", ".join(target_symptoms) if target_symptoms else ""

    product_info = (
        f"상품명: {name} ({form})\n"
        f"섭취방법: {dosage}\n"
        f"소구점: {headline}\n"
        f"기전: {mechanism}\n"
        f"핵심성분: {key_ingredients}\n"
        f"타겟증상: {symptoms_str}\n"
        f"대체솔루션: {competitor_alt}\n"
        f"판매실적: {asset_labels}\n"
        f"가격: {pricing_str}\n"
        f"판매채널: {cta_channel}"
    )

    return {
        "product_id": str(videofactory_product_id),
        "product_info": product_info,
    }


def fetch_single_script(ad_id: str) -> str:
    with get_db() as (conn, cur):
        cur.execute(
            "SET search_path = ad_reference_dash; SELECT script_text FROM ad_scripts WHERE ad_id = %s AND status = 'completed'",
            (ad_id,)
        )
        row = cur.fetchone()
    return row[0]


def generate_script_lines(ref_script: str, script_type: str, product_info: str = "") -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    product_info_line = product_info if product_info else "제품 정보 없음 - 원본 원고의 내용을 최대한 유지"

    prompt = f"""당신은 광고 원고 이식 전문가입니다.

## 핵심 규칙 (반드시 준수)
1. 아래 "원본 원고"의 문장 구조, 어투, 흐름을 **그대로 유지**하세요.
2. 원본 원고에서 **상품명, 성분, 기전, 효능** 부분만 아래 제품 정보로 교체하세요.
3. 원본의 감정적 표현, 후킹 문구, 말투는 **절대 변경하지 마세요**.
4. 새로운 문장을 추가하거나 원본에 없는 내용을 창작하지 마세요.
5. 원본 원고의 길이와 최대한 비슷하게 유지하세요.

## 교체할 제품 정보
{product_info_line}

## 원본 원고 (구조 유지, 제품 정보만 교체)
{ref_script}

---
위 원본 원고의 구조와 워딩을 최대한 유지하면서, 제품 관련 내용만 위 제품 정보로 교체한 원고를 JSON 배열로 출력하세요.
원고를 문장/호흡 단위로 나눠 배열로 출력하세요: ["라인1", "라인2", ...]
순수 JSON 배열만 출력하세요. 다른 설명, 마크다운, 코드블록 없이."""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    raw = response.text.strip()

    # JSON 배열 파싱
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    script_lines = json.loads(raw)
    return script_lines


def post_concept(product_id: str, title: str, script_lines: list[str], videofactory_url: str) -> dict:
    url = f"{videofactory_url.rstrip('/')}/api/concepts"
    payload = {
        "product_id": product_id,
        "title": title,
        "script_lines": script_lines,
    }
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main(
    product_id: str | None,
    title: str,
    script_type: str,
    ref_count: int,
    advertiser: str | None,
    videofactory_url: str,
    dry_run: bool,
    product_info: str = "",
    base_ad_id: str = None,
    product_slug: str = None,
    selling_point: str = None,
) -> dict:
    if product_slug:
        if not selling_point:
            raise ValueError("--product-slug 사용 시 --selling-point 도 필수입니다.")
        fetched = fetch_product_from_db(product_slug, selling_point)
        product_id = fetched["product_id"]
        product_info = fetched["product_info"]

    if not product_id:
        raise ValueError("--product-id 또는 --product-slug 중 하나는 반드시 지정해야 합니다.")

    if base_ad_id:
        ref_script = fetch_single_script(base_ad_id)
        fetched_ref_count = 1
    else:
        ref_scripts = fetch_ref_scripts(ref_count, advertiser)
        ref_script = max(ref_scripts, key=lambda r: len(r["script_text"]))["script_text"]
        fetched_ref_count = len(ref_scripts)

    script_lines = generate_script_lines(ref_script, script_type, product_info)

    concept_id = None
    if not dry_run:
        concept = post_concept(product_id, title, script_lines, videofactory_url)
        concept_id = concept.get("id")

    return {
        "title": title,
        "script_type": script_type,
        "product_slug": product_slug,
        "selling_point": selling_point,
        "product_info": product_info,
        "ref_count": fetched_ref_count,
        "base_ad_id": base_ad_id or "random",
        "generated_script_lines": script_lines,
        "concept_id": concept_id,
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="광고 레퍼런스 원고 → 자동 원고 생성기")
    parser.add_argument("--product-id", default=None, help="video-factory product ID (--product-slug 미사용 시 필수)")
    parser.add_argument("--product-slug", default=None, help="DB 상품 slug (예: salladit-cca)")
    parser.add_argument("--selling-point", default=None, help="소구점 label (--product-slug 사용 시 필수, 예: 간편디톡스)")
    parser.add_argument("--title", required=True, help="concept 제목")
    parser.add_argument("--script-type", required=True, choices=["정보성", "후기성", "프로모션"], help="원고 유형")
    parser.add_argument("--ref-count", type=int, default=5, help="참고할 레퍼런스 원고 수 (기본: 5)")
    parser.add_argument("--advertiser", default=None, help="특정 광고주 필터 (선택)")
    parser.add_argument("--videofactory-url", default="http://localhost:8001", help="video-factory API URL")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 생성 원고만 출력")
    parser.add_argument("--product-info", default="", help="제품 소구점/USP/기전 설명 (자유 텍스트)")
    parser.add_argument("--base-ad-id", default=None, help="베이스로 사용할 특정 ad_id (미지정시 랜덤 선택)")
    args = parser.parse_args()

    if not args.product_slug and not args.product_id:
        parser.error("--product-id 또는 --product-slug 중 하나는 반드시 지정해야 합니다.")

    result = main(
        product_id=args.product_id,
        title=args.title,
        script_type=args.script_type,
        ref_count=args.ref_count,
        advertiser=args.advertiser,
        videofactory_url=args.videofactory_url,
        dry_run=args.dry_run,
        product_info=args.product_info,
        base_ad_id=args.base_ad_id,
        product_slug=args.product_slug,
        selling_point=args.selling_point,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"generate_concept_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
