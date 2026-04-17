import argparse
import json
from datetime import datetime
from pathlib import Path

from conn import get_db
from utils.serialize import rows_to_dicts


def list_all_users() -> list[dict]:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, email, name, company, job_title, role, is_approved, created_at FROM users ORDER BY created_at"
        )
        rows = rows_to_dicts(cur)
    return rows


def main() -> dict:
    users = list_all_users()
    return {"users": users, "total": len(users)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List all users (admin)")
    parser.parse_args()

    result = main()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"list_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Saved: {output_file}")
