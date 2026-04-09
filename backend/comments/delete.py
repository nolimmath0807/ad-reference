import argparse

from fastapi import HTTPException

from conn import get_db


def delete_comment(comment_id: str, requester_id: str, is_admin: bool) -> None:
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id, user_id FROM ad_comments WHERE id = %s::uuid",
            (comment_id,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "COMMENT_NOT_FOUND", "message": "댓글을 찾을 수 없습니다.", "details": None}},
            )

        if not is_admin and str(row[1]) != requester_id:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "FORBIDDEN", "message": "삭제 권한이 없습니다.", "details": None}},
            )

        cur.execute("DELETE FROM ad_comments WHERE id = %s::uuid", (comment_id,))
        conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a comment")
    parser.add_argument("--comment-id", required=True)
    parser.add_argument("--requester-id", required=True)
    parser.add_argument("--is-admin", action="store_true")
    args = parser.parse_args()

    delete_comment(args.comment_id, args.requester_id, args.is_admin)
    print("Deleted successfully")
