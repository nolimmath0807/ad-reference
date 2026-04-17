import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from conn import get_db

load_dotenv()


def migrate(dry_run: bool) -> dict:
    with get_db() as (conn, cur):
        # 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ad_reference_dash.products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                form TEXT,
                dosage TEXT,
                cta_channel TEXT,
                videofactory_product_id UUID,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ad_reference_dash.product_selling_points (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_id UUID NOT NULL REFERENCES ad_reference_dash.products(id) ON DELETE CASCADE,
                label TEXT NOT NULL,
                headline TEXT,
                mechanism TEXT,
                key_ingredients TEXT,
                target_symptoms TEXT[],
                competitor_alt TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ad_reference_dash.product_assets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_id UUID NOT NULL REFERENCES ad_reference_dash.products(id) ON DELETE CASCADE,
                asset_key TEXT NOT NULL,
                asset_value TEXT NOT NULL,
                asset_label TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ad_reference_dash.product_pricing (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_id UUID NOT NULL REFERENCES ad_reference_dash.products(id) ON DELETE CASCADE,
                option_name TEXT NOT NULL,
                price INT,
                original_price INT,
                discount_rate INT,
                daily_price INT,
                is_main BOOLEAN DEFAULT FALSE
            )
        """)

        if dry_run:
            conn.rollback()
            return {"status": "dry_run", "message": "테이블 DDL만 실행 (롤백됨)"}

        # 샐러디트 CCA 샐러드 초기 데이터 INSERT (중복 방지)
        cur.execute("""
            INSERT INTO ad_reference_dash.products
                (slug, name, form, dosage, cta_channel, videofactory_product_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO NOTHING
            RETURNING id
        """, (
            "salladit-cca",
            "샐러디트 CCA 샐러드",
            "물 없이 씹어서 섭취하는 츄어블 캔디",
            "하루 1정, 간편하게 씹어서 섭취",
            "샐러디트 자사몰",
            "2a170656-bfe0-4c1e-81f1-6e30b9ea9bef",
        ))
        row = cur.fetchone()

        if row is None:
            # 이미 존재하는 경우 id 조회
            cur.execute(
                "SELECT id FROM ad_reference_dash.products WHERE slug = %s",
                ("salladit-cca",),
            )
            product_id = str(cur.fetchone()[0])
            sp_count = asset_count = pricing_count = 0
            print(f"[SKIP] 샐러디트 CCA 이미 존재: product_id={product_id}")
        else:
            product_id = str(row[0])

            # 소구점 4개
            selling_points = [
                (
                    "간편디톡스",
                    "한 알로 끝내는 CCA 루틴",
                    "당근·양배추·사과의 식이섬유가 배변 활동을 원활하게 하여 바쁜 일상에서 가볍게 비워주는 디톡스 루틴을 완성한다",
                    "당근(Carrot), 양배추(Cabbage), 사과(Apple) 식이섬유",
                    ["기름진 식사 후 죄책감", "몸이 무겁고 더부룩한 느낌", "속이 꽉 막힌 느낌", "바쁜 일상으로 채소 챙기기 힘든 상황"],
                    "매일 직접 채소를 갈아 마시는 CCA 주스",
                ),
                (
                    "야채12kg",
                    "한 통에 채소 12kg 영양소 압축",
                    "한 통에 당근 2.4kg, 사과 3.6kg, 양배추 6kg 분량의 영양소가 압축되어 있어 매일 채소를 손질하지 않고도 하루 필요 과채 영양을 한 알로 보충할 수 있다",
                    "당근 2.4kg + 사과 3.6kg + 양배추 6kg 분량 함유",
                    ["채소 섭취량이 부족한 상태(성인 22.1%만 충분히 섭취)", "불규칙한 식사로 영양 불균형", "바쁜 스케줄로 식단 관리 어려움"],
                    "유산균, 일반 비타민 영양제",
                ),
                (
                    "이중항산화",
                    "알파리포산 + 폴리페놀 시너지로 산뜻한 리셋",
                    "시금치 유래 알파리포산이 체내 항산화 네트워크에 관여해 산화 스트레스를 완화하고, 올리브잎 폴리페놀과의 시너지로 바쁜 일상을 산뜻하게 리셋한다",
                    "시금치 추출 알파리포산, 올리브잎 폴리페놀, 인디언구스베리(비타민C/갈로탄닌)",
                    ["피로감이 쌓이는 바쁜 일상", "컨디션 관리가 필요한 상황", "산화 스트레스로 인한 피로"],
                    "일반 항산화 비타민제",
                ),
                (
                    "다이어트정체기",
                    "라인·체지방 관리를 위한 CCA 3종 배합",
                    "당근(라인 관리), 양배추(붓기 관리), 사과(체지방 관리)의 3종 조합이 다이어트 정체기를 극복하고 체형 관리를 돕는다",
                    "당근(라인 관리), 양배추(붓기 관리), 사과(체지방 관리)",
                    ["다이어트 정체기로 지쳐있는 상황", "붓기가 빠지지 않는 상태", "체지방 관리가 필요한 상황"],
                    "다이어트 보조제, 부스터",
                ),
            ]

            for label, headline, mechanism, key_ingredients, target_symptoms, competitor_alt in selling_points:
                cur.execute("""
                    INSERT INTO ad_reference_dash.product_selling_points
                        (product_id, label, headline, mechanism, key_ingredients, target_symptoms, competitor_alt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (product_id, label, headline, mechanism, key_ingredients, target_symptoms, competitor_alt))
            sp_count = len(selling_points)

            # 에셋 6개
            assets = [
                ("sales_count", "60만 개 이상", "누적 판매 60만 개 이상"),
                ("rating", "4.9", "소비자 만족도 4.9/5.0"),
                ("restock_count", "8차", "현재 8차 입고 완료"),
                ("discount_rate", "46", "최대 46% 할인"),
                ("award_2026", "2026 올해의 소비자 만족지수 1위", "2026 올해의 소비자 만족지수 1위"),
                ("certification", "HACCP", "HACCP 인증 제조 시설 생산"),
            ]

            for asset_key, asset_value, asset_label in assets:
                cur.execute("""
                    INSERT INTO ad_reference_dash.product_assets
                        (product_id, asset_key, asset_value, asset_label)
                    VALUES (%s, %s, %s, %s)
                """, (product_id, asset_key, asset_value, asset_label))
            asset_count = len(assets)

            # 가격 옵션 2개
            pricings = [
                ("5+5 Box", 272000, 500000, 46, 900, True),
                ("단품", 31500, 58000, 46, 1050, False),
            ]

            for option_name, price, original_price, discount_rate, daily_price, is_main in pricings:
                cur.execute("""
                    INSERT INTO ad_reference_dash.product_pricing
                        (product_id, option_name, price, original_price, discount_rate, daily_price, is_main)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (product_id, option_name, price, original_price, discount_rate, daily_price, is_main))
            pricing_count = len(pricings)

        return {
            "product_id": product_id,
            "selling_points_inserted": sp_count,
            "assets_inserted": asset_count,
            "pricing_inserted": pricing_count,
        }


def main(dry_run: bool) -> dict:
    result = migrate(dry_run)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ad_reference_dash 상품 테이블 마이그레이션 + 샐러디트 초기 데이터 INSERT")
    parser.add_argument("--dry-run", action="store_true", help="테이블 생성만 확인하고 롤백 (데이터 INSERT 없음)")
    args = parser.parse_args()

    result = main(dry_run=args.dry_run)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"migrate_product_tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
