import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from conn import get_db

load_dotenv()

SELLING_POINT_UPDATES = [
    {
        "old_label": "간편디톡스",
        "label": "디톡스",
        "headline": "한 알로 완성하는 CCA 디톡스 루틴",
        "mechanism": "당근·양배추·사과 식이섬유와 알파리포산, 폴리페놀의 항산화 시너지로 체내 독소를 배출하고 가볍게 비워주는 디톡스 루틴을 완성한다",
        "key_ingredients": "당근·양배추·사과 식이섬유, 시금치 알파리포산, 올리브잎 폴리페놀",
        "target_symptoms": ["아침마다 얼굴이 붓는 증상", "기름진 식사 후 몸이 무겁고 더부룩한 느낌", "독소가 쌓이는 느낌", "저녁만 되면 다리가 퉁퉁 붓는 증상"],
    },
    {
        "old_label": "이중항산화",
        "label": "식전보호막",
        "headline": "식사 전 천연 보호막으로 혈당 스파이크 차단",
        "mechanism": "사과와 양배추의 천연 식이섬유가 식전 보호막을 형성하여 식후 혈당 스파이크를 완화하고, 올리브잎 폴리페놀이 식후 컨디션을 리셋한다",
        "key_ingredients": "사과·양배추 천연 식이섬유, 올리브잎 폴리페놀",
        "target_symptoms": ["밥 먹기 전 혈당 걱정", "식후 급격한 혈당 상승", "식사 후 무기력함", "달달한 음식 먹은 후 혈당 스파이크"],
    },
    {
        "old_label": "야채12kg",
        "label": "야채12kg",
        "headline": "한 통에 채소 12kg 영양소 압축",
        "mechanism": "한 통에 당근 2.4kg, 사과 3.6kg, 양배추 6kg 분량의 영양소가 압축되어 있어 하루 한 알로 12kg 야채의 영양을 흡수할 수 있다",
        "key_ingredients": "당근 2.4kg + 사과 3.6kg + 양배추 6kg 분량 함유",
        "target_symptoms": ["채소 섭취량이 부족한 상태 (성인 22.1%만 충분히 섭취)", "불규칙한 식사로 영양 불균형", "바쁜 스케줄로 식단 관리가 어려운 상황"],
    },
    {
        "old_label": "다이어트정체기",
        "label": "변비숙변",
        "headline": "천연 식이섬유로 숙변 제거, 변비 해결",
        "mechanism": "당근·양배추·사과의 천연 식이섬유가 장 운동을 활성화하고 묵은 숙변을 밀어내어 변비를 해결하며, 가볍고 편안한 장 환경을 만든다",
        "key_ingredients": "당근·양배추·사과 천연 식이섬유",
        "target_symptoms": ["아침마다 배가 묵직한 느낌", "변비로 인한 더부룩함", "묵은 숙변으로 불쾌한 느낌", "장 운동이 느린 상태"],
    },
]


def main(slug: str) -> dict:
    updated = []

    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id FROM ad_reference_dash.products WHERE slug = %s",
            (slug,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"상품을 찾을 수 없습니다: slug={slug}")
        product_id = str(row[0])

        for sp in SELLING_POINT_UPDATES:
            cur.execute(
                """
                UPDATE ad_reference_dash.product_selling_points
                SET label = %s,
                    headline = %s,
                    mechanism = %s,
                    key_ingredients = %s,
                    target_symptoms = %s
                WHERE product_id = %s AND label = %s
                RETURNING id, label
                """,
                (
                    sp["label"],
                    sp["headline"],
                    sp["mechanism"],
                    sp["key_ingredients"],
                    sp["target_symptoms"],
                    product_id,
                    sp["old_label"],
                ),
            )
            result_row = cur.fetchone()
            if result_row:
                updated.append({"id": str(result_row[0]), "label": result_row[1]})
                print(f"[OK] {sp['old_label']} → {sp['label']}")
            else:
                print(f"[SKIP] {sp['old_label']} — 해당 레이블 없음")

    return {
        "slug": slug,
        "updated_count": len(updated),
        "updated_labels": [u["label"] for u in updated],
        "details": updated,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="salladit-cca 소구점 레이블/기전 업데이트")
    parser.add_argument("--slug", default="salladit-cca", help="상품 slug (기본: salladit-cca)")
    args = parser.parse_args()

    result = main(slug=args.slug)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"update_selling_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
