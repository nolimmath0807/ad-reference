import argparse
import json
from datetime import datetime
from pathlib import Path

from conn import get_db


def list_all_users() -> list[dict]:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, email, name, company, job_title, role, created_at FROM users ORDER BY created_at"
        )
        cols = [desc[0] for desc in cur.description]
        rows = []
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
                elif hasattr(v, "hex"):
                    d[k] = str(v)
            rows.append(d)
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
