import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ads.generate_concept_script import fetch_product_from_db, generate_script_lines

load_dotenv()

VIDEOFACTORY_URL = "http://localhost:8100"

KEYWORD_TO_SELLING_POINT = {
    "디톡스": "디톡스",
    "식전보호막": "식전보호막",
    "야채12kg": "야채12kg",
    "야채": "야채12kg",
    "변비": "변비숙변",
    "숙변": "변비숙변",
}


def classify_selling_point(title: str) -> str | None:
    for keyword, selling_point in KEYWORD_TO_SELLING_POINT.items():
        if keyword in title:
            return selling_point
    return None


def fetch_all_concepts(limit: int = 200) -> list[dict]:
    url = f"{VIDEOFACTORY_URL}/api/concepts"
    resp = httpx.get(url, params={"limit": limit}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("items", data.get("data", []))


def fetch_concept_detail(concept_id: str) -> dict:
    url = f"{VIDEOFACTORY_URL}/api/concepts/{concept_id}"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def put_concept(concept_id: str, script_lines: list[str]) -> dict:
    url = f"{VIDEOFACTORY_URL}/api/concepts/{concept_id}"
    resp = httpx.put(url, json={"script_lines": script_lines}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def process_concept(concept: dict, dry_run: bool) -> dict:
    concept_id = str(concept["id"])
    title = concept.get("title", "")

    selling_point = classify_selling_point(title)
    if selling_point is None:
        return {"concept_id": concept_id, "title": title, "status": "skipped", "reason": "분류 불가"}

    detail = fetch_concept_detail(concept_id)
    script_lines_list = detail.get("script_lines", [])

    if not script_lines_list:
        return {"concept_id": concept_id, "title": title, "selling_point": selling_point, "status": "skipped", "reason": "script_lines 없음"}

    ref_script = "\n".join(script_lines_list) if script_lines_list else ""

    fetched = fetch_product_from_db("salladit-cca", selling_point)
    product_info = fetched["product_info"]

    time.sleep(0.5)

    new_script_lines = generate_script_lines(ref_script, "후기성", product_info)

    if dry_run:
        return {
            "concept_id": concept_id,
            "title": title,
            "selling_point": selling_point,
            "status": "dry_run",
            "new_script_lines": new_script_lines,
        }

    put_concept(concept_id, new_script_lines)
    return {
        "concept_id": concept_id,
        "title": title,
        "selling_point": selling_point,
        "status": "updated",
        "script_line_count": len(new_script_lines),
    }


def main(dry_run: bool, selling_point_filter: str | None, concurrency: int) -> dict:
    all_concepts = fetch_all_concepts()
    cca_concepts = [c for c in all_concepts if "CCA" in c.get("title", "")]

    if selling_point_filter:
        cca_concepts = [c for c in cca_concepts if classify_selling_point(c.get("title", "")) == selling_point_filter]

    print(f"[INFO] 총 {len(cca_concepts)}개 CCA concept 처리 예정")

    if dry_run:
        if not cca_concepts:
            return {"dry_run": True, "message": "처리할 concept 없음", "results": []}
        result = process_concept(cca_concepts[0], dry_run=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {"dry_run": True, "results": [result]}

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(process_concept, c, False): c for c in cca_concepts}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            status = res.get("status", "unknown")
            title = res.get("title", "")
            concept_id = res.get("concept_id", "")
            sp = res.get("selling_point", "-")
            print(f"[{status.upper()}] {concept_id} | {sp} | {title}")

    success = [r for r in results if r.get("status") == "updated"]
    skipped = [r for r in results if r.get("status") == "skipped"]
    failed = [r for r in results if r.get("status") == "failed"]

    return {
        "total": len(cca_concepts),
        "updated": len(success),
        "skipped": len(skipped),
        "failed": len(failed),
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="video-factory CCA concept script_lines 일괄 재생성/업데이트")
    parser.add_argument("--dry-run", action="store_true", help="PUT 없이 첫 번째 concept 재생성 결과만 출력")
    parser.add_argument("--selling-point", default=None, help="특정 소구점만 처리 (예: 디톡스, 식전보호막, 야채12kg, 변비숙변)")
    parser.add_argument("--concurrency", type=int, default=3, help="동시 처리 수 (기본: 3)")
    args = parser.parse_args()

    result = main(
        dry_run=args.dry_run,
        selling_point_filter=args.selling_point,
        concurrency=args.concurrency,
    )

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"batch_update_concepts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
