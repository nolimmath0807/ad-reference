import json
import os
import uuid
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path as FilePath

from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, Query, Path, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from auth.login import login
from auth.register import register
from auth.logout import logout
from auth.model import LoginRequest, RegisterRequest, LogoutRequest

from ads.search import search_ads
from ads.detail import get_ad_detail
from ads.save import save_ad
from ads.model import AdSaveRequest

from boards.create import create_board
from boards.list import list_boards
from boards.detail import get_board_detail
from boards.add_item import add_board_item
from boards.remove_item import remove_board_item
from boards.model import BoardCreateRequest, BoardItemAddRequest

from users.profile import get_profile
from users.update import update_profile
from users.model import UserUpdateRequest

from platforms.model import PlatformStatus, PlatformType, Status
from platforms.batch_collector import run_daily_batch

from conn import get_db

from utils.auth_helper import get_current_user

app = FastAPI(title="Ad Reference API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FilePath("static/screenshots").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBearer()


async def get_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return user


def _check_error(result: dict) -> dict:
    if "error" in result:
        error = result["error"]
        code = error.get("code", "INTERNAL_SERVER_ERROR")
        status_map = {
            "BAD_REQUEST": 400,
            "UNAUTHORIZED": 401,
            "NOT_FOUND": 404,
            "CONFLICT": 409,
        }
        status_code = status_map.get(code, 500)
        raise HTTPException(status_code=status_code, detail=result)
    return result


# ──────────────────────────────────────────────
# Auth (public - no JWT required)
# ──────────────────────────────────────────────

@app.post("/auth/register", status_code=201)
async def api_register(request: RegisterRequest):
    return register(request)


@app.post("/auth/login")
async def api_login(request: LoginRequest):
    return login(request)


@app.post("/auth/logout")
async def api_logout(request: LogoutRequest):
    return logout(request.refresh_token)


# ──────────────────────────────────────────────
# Ads (JWT required)
# ──────────────────────────────────────────────

@app.get("/ads/search")
async def api_search_ads(
    user: dict = Depends(get_user),
    keyword: Optional[str] = Query(default=None),
    platform: str = Query(default="all"),
    format: str = Query(default="all"),
    sort: str = Query(default="recent"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    industry: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await search_ads(keyword, platform, format, sort, date_from, date_to, industry, page, limit)


@app.get("/ads/{ad_id}")
async def api_get_ad_detail(
    ad_id: str = Path(...),
    user: dict = Depends(get_user),
):
    return get_ad_detail(ad_id)


@app.post("/ads/save", status_code=201)
async def api_save_ad(
    request: AdSaveRequest,
    user: dict = Depends(get_user),
):
    return save_ad(request)


# ──────────────────────────────────────────────
# Boards (JWT required)
# ──────────────────────────────────────────────

@app.post("/boards", status_code=201)
async def api_create_board(
    request: BoardCreateRequest,
    user: dict = Depends(get_user),
):
    return create_board(user["user_id"], request.name, request.description or "")


@app.get("/boards")
async def api_list_boards(
    user: dict = Depends(get_user),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=50),
):
    return list_boards(user["user_id"], page, limit)


@app.get("/boards/{board_id}")
async def api_get_board_detail(
    board_id: str = Path(...),
    user: dict = Depends(get_user),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
):
    return get_board_detail(board_id, user["user_id"], page, limit)


@app.post("/boards/{board_id}/items", status_code=201)
async def api_add_board_item(
    request: BoardItemAddRequest,
    board_id: str = Path(...),
    user: dict = Depends(get_user),
):
    return add_board_item(board_id, request.ad_id, user["user_id"])


@app.delete("/boards/{board_id}/items/{item_id}")
async def api_remove_board_item(
    board_id: str = Path(...),
    item_id: str = Path(...),
    user: dict = Depends(get_user),
):
    return remove_board_item(board_id, item_id, user["user_id"])


# ──────────────────────────────────────────────
# Users (JWT required)
# ──────────────────────────────────────────────

@app.get("/users/me")
async def api_get_profile(user: dict = Depends(get_user)):
    result = get_profile(user["user_id"])
    return _check_error(result)


@app.put("/users/me")
async def api_update_profile(
    request: UserUpdateRequest,
    user: dict = Depends(get_user),
):
    result = update_profile(
        user_id=user["user_id"],
        name=request.name,
        company=request.company,
        job_title=request.job_title,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return _check_error(result)


# ──────────────────────────────────────────────
# Crawl (JWT required)
# ──────────────────────────────────────────────

class CrawlRequest(BaseModel):
    keyword: str
    platforms: list[str] = Field(default=["meta", "google"])
    search_type: str = Field(default="keyword")
    max_results: int = Field(default=12, ge=1, le=50)


_crawl_jobs: dict[str, dict] = {}


def _run_crawl_job(job_id: str, keyword: str, platforms: list[str], search_type: str, max_results: int):
    _crawl_jobs[job_id]["status"] = "running"
    try:
        from platforms.scrape_worker import run_crawl
        result = run_crawl(keyword, platforms, search_type, max_results)
        _crawl_jobs[job_id]["status"] = "completed"
        _crawl_jobs[job_id]["result"] = result
    except Exception as e:
        _crawl_jobs[job_id]["status"] = "failed"
        _crawl_jobs[job_id]["error"] = str(e)


@app.post("/crawl", status_code=202)
async def api_start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_user),
):
    job_id = uuid.uuid4().hex[:12]
    _crawl_jobs[job_id] = {
        "job_id": job_id,
        "status": "started",
        "keyword": request.keyword,
        "platforms": request.platforms,
    }
    background_tasks.add_task(
        _run_crawl_job, job_id, request.keyword, request.platforms,
        request.search_type, request.max_results,
    )
    return {"job_id": job_id, "status": "started", "keyword": request.keyword}


@app.get("/crawl/{job_id}")
async def api_crawl_status(
    job_id: str = Path(...),
    user: dict = Depends(get_user),
):
    job = _crawl_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ──────────────────────────────────────────────
# Platforms (JWT required)
# ──────────────────────────────────────────────

@app.get("/platforms/status")
async def api_platforms_status(user: dict = Depends(get_user)):
    platforms = [
        PlatformStatus(
            platform=PlatformType.meta,
            status=Status.active,
            message="Meta Ad Library (Playwright 스크래퍼)",
        ),
        PlatformStatus(
            platform=PlatformType.google,
            status=Status.active if os.environ.get("SERPAPI_KEY") else Status.unavailable,
            message="Google Ads (SerpAPI) 연동" if os.environ.get("SERPAPI_KEY") else None,
        ),
        PlatformStatus(
            platform=PlatformType.tiktok,
            status=Status.active if os.environ.get("TIKTOK_API_KEY") else Status.unavailable,
            message="TikTok Creative Center 연동" if os.environ.get("TIKTOK_API_KEY") else None,
        ),
        PlatformStatus(
            platform=PlatformType.instagram,
            status=Status.active if os.environ.get("META_ACCESS_TOKEN") else Status.unavailable,
            message="Instagram (Meta API) 연동" if os.environ.get("META_ACCESS_TOKEN") else None,
        ),
    ]
    return {"platforms": [p.model_dump(mode="json") for p in platforms]}


# ──────────────────────────────────────────────
# Monitored Domains (JWT required)
# ──────────────────────────────────────────────

class MonitoredDomainRequest(BaseModel):
    domain: str
    platform: str = "google"
    notes: str | None = None


class MonitoredDomainUpdate(BaseModel):
    is_active: bool | None = None
    notes: str | None = None


@app.get("/monitored-domains")
async def api_list_monitored_domains(
    user: dict = Depends(get_user),
    is_active: Optional[bool] = Query(default=None),
):
    with get_db() as (conn, cur):
        if is_active is not None:
            cur.execute(
                "SELECT * FROM monitored_domains WHERE is_active = %s ORDER BY created_at DESC",
                (is_active,),
            )
        else:
            cur.execute("SELECT * FROM monitored_domains ORDER BY created_at DESC")
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    for row in rows:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif isinstance(v, uuid.UUID):
                row[k] = str(v)
    return {"domains": rows}


@app.post("/monitored-domains", status_code=201)
async def api_create_monitored_domain(
    request: MonitoredDomainRequest,
    user: dict = Depends(get_user),
):
    with get_db() as (conn, cur):
        cur.execute(
            "SELECT id FROM monitored_domains WHERE domain = %s",
            (request.domain,),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"도메인 '{request.domain}'이 이미 등록되어 있습니다.")
        cur.execute(
            "INSERT INTO monitored_domains (domain, platform, notes) VALUES (%s, %s, %s) RETURNING *",
            (request.domain, request.platform, request.notes),
        )
        cols = [desc[0] for desc in cur.description]
        row = dict(zip(cols, cur.fetchone()))
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            row[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            row[k] = str(v)
    return row


@app.put("/monitored-domains/{domain_id}")
async def api_update_monitored_domain(
    request: MonitoredDomainUpdate,
    domain_id: str = Path(...),
    user: dict = Depends(get_user),
):
    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM monitored_domains WHERE id = %s::uuid", (domain_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="도메인을 찾을 수 없습니다.")

        updates = []
        values = []
        if request.is_active is not None:
            updates.append("is_active = %s")
            values.append(request.is_active)
        if request.notes is not None:
            updates.append("notes = %s")
            values.append(request.notes)

        if not updates:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")

        updates.append("updated_at = NOW()")
        values.append(domain_id)

        cur.execute(
            f"UPDATE monitored_domains SET {', '.join(updates)} WHERE id = %s::uuid RETURNING *",
            values,
        )
        cols = [desc[0] for desc in cur.description]
        row = dict(zip(cols, cur.fetchone()))
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            row[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            row[k] = str(v)
    return row


@app.delete("/monitored-domains/{domain_id}")
async def api_delete_monitored_domain(
    domain_id: str = Path(...),
    user: dict = Depends(get_user),
):
    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM monitored_domains WHERE id = %s::uuid", (domain_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="도메인을 찾을 수 없습니다.")
        cur.execute("DELETE FROM monitored_domains WHERE id = %s::uuid", (domain_id,))
    return {"message": "도메인이 삭제되었습니다."}


@app.get("/monitored-domains/{domain_id}/ads")
async def api_monitored_domain_ads(
    domain_id: str = Path(...),
    user: dict = Depends(get_user),
    platform: str = Query(default="all"),
    format: str = Query(default="all"),
    sort: str = Query(default="recent"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    with get_db() as (conn, cur):
        # 1. monitored_domains에서 domain 조회
        cur.execute(
            "SELECT domain FROM monitored_domains WHERE id = %s::uuid",
            (domain_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="도메인을 찾을 수 없습니다.")
        domain_name = row[0]

        # 2. WHERE 조건 구성 (www. 접두사 무시 + domain NULL fallback)
        bare_domain = domain_name.replace("www.", "")
        conditions = [
            "(REPLACE(domain, 'www.', '') = %s OR (domain IS NULL AND landing_page_url LIKE %s))"
        ]
        params: list = [bare_domain, f"%{bare_domain}%"]

        # 비정상 썸네일 필터 (HTML 페이지 URL, 빈 문자열 제외)
        conditions.append("thumbnail_url != ''")
        conditions.append("thumbnail_url NOT LIKE '%%.html%%'")

        if platform != "all":
            conditions.append("platform = %s")
            params.append(platform)
        if format == "all":
            conditions.append("format != 'text'")
        elif format != "all":
            conditions.append("format = %s")
            params.append(format)

        where = " AND ".join(conditions)
        order = "created_at DESC" if sort == "recent" else "created_at ASC"
        offset = (page - 1) * limit

        # 3. total count
        cur.execute(f"SELECT COUNT(*) FROM ads WHERE {where}", params)
        total = cur.fetchone()[0]

        # 4. 광고 목록 조회
        cur.execute(
            f"""
            SELECT id, platform, format, advertiser_name, advertiser_handle,
                   advertiser_avatar_url, thumbnail_url, preview_url, media_type,
                   ad_copy, cta_text, likes, comments, shares,
                   start_date, end_date, tags, landing_page_url, domain,
                   created_at, saved_at
            FROM ads
            WHERE {where}
            ORDER BY {order}
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        cols = [desc[0] for desc in cur.description]
        items = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
                elif isinstance(v, uuid.UUID):
                    d[k] = str(v)
            items.append(d)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total,
    }


@app.get("/monitored-domains/{domain_id}/stats")
async def api_monitored_domain_stats(
    domain_id: str = Path(...),
    user: dict = Depends(get_user),
):
    with get_db() as (conn, cur):
        # 1. monitored_domains 정보 조회
        cur.execute(
            "SELECT * FROM monitored_domains WHERE id = %s::uuid",
            (domain_id,),
        )
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="도메인을 찾을 수 없습니다.")
        domain_info = dict(zip(cols, row))
        domain_name = domain_info["domain"]

        # Serialize domain_info
        for k, v in domain_info.items():
            if hasattr(v, "isoformat"):
                domain_info[k] = v.isoformat()
            elif isinstance(v, uuid.UUID):
                domain_info[k] = str(v)

        # 2. total_ads (www. 접두사 무시 + domain NULL fallback)
        bare_domain = domain_name.replace("www.", "")
        domain_filter = (
            "(REPLACE(domain, 'www.', '') = %s OR (domain IS NULL AND landing_page_url LIKE %s))"
            " AND thumbnail_url != ''"
            " AND thumbnail_url NOT LIKE '%%.html%%'"
        )
        domain_params = [bare_domain, f"%{bare_domain}%"]

        cur.execute(f"SELECT COUNT(*) FROM ads WHERE {domain_filter}", domain_params)
        total_ads = cur.fetchone()[0]

        # 3. ads_by_format
        cur.execute(
            f"SELECT format, COUNT(*) FROM ads WHERE {domain_filter} GROUP BY format",
            domain_params,
        )
        ads_by_format = {row[0]: row[1] for row in cur.fetchall()}

        # 4. ads_by_platform
        cur.execute(
            f"SELECT platform, COUNT(*) FROM ads WHERE {domain_filter} GROUP BY platform",
            domain_params,
        )
        ads_by_platform = {row[0]: row[1] for row in cur.fetchall()}

        # 5. last_collected_at
        cur.execute(
            f"SELECT MAX(COALESCE(updated_at, created_at)) FROM ads WHERE {domain_filter}",
            domain_params,
        )
        last_row = cur.fetchone()[0]
        last_collected_at = last_row.isoformat() if last_row else None

    return {
        "domain_info": domain_info,
        "total_ads": total_ads,
        "ads_by_format": ads_by_format,
        "ads_by_platform": ads_by_platform,
        "last_collected_at": last_collected_at,
    }


# ──────────────────────────────────────────────
# Batch Operations (JWT required)
# ──────────────────────────────────────────────

class BatchRunRequest(BaseModel):
    domain: str | None = None
    mode: str = "full"  # "full" or "incremental"


_batch_jobs: dict[str, dict] = {}


def _run_batch_job(job_id: str, domain: str | None, mode: str = "full"):
    _batch_jobs[job_id]["status"] = "running"
    result = run_daily_batch(trigger_type="manual", domain=domain or "", mode=mode)
    _batch_jobs[job_id]["status"] = "completed"
    _batch_jobs[job_id]["result"] = result


@app.post("/batch/run", status_code=202)
async def api_run_batch(
    request: BatchRunRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_user),
):
    job_id = uuid.uuid4().hex[:12]
    _batch_jobs[job_id] = {
        "job_id": job_id,
        "status": "started",
        "domain": request.domain,
        "mode": request.mode,
    }
    background_tasks.add_task(_run_batch_job, job_id, request.domain, request.mode)
    return {"job_id": job_id, "status": "started", "domain": request.domain, "mode": request.mode}


def _serialize_batch_row(row: dict) -> dict:
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            row[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            row[k] = str(v)
        elif isinstance(v, dict) or isinstance(v, list):
            pass  # already JSON-compatible
    return row


@app.get("/batch/runs")
async def api_list_batch_runs(
    user: dict = Depends(get_user),
    limit: int = Query(default=20, ge=1, le=100),
):
    with get_db() as (conn, cur):
        cur.execute("SELECT * FROM batch_runs ORDER BY started_at DESC LIMIT %s", (limit,))
        cols = [desc[0] for desc in cur.description]
        rows = [_serialize_batch_row(dict(zip(cols, row))) for row in cur.fetchall()]
    return {"runs": rows}


@app.get("/batch/runs/latest")
async def api_latest_batch_run(user: dict = Depends(get_user)):
    with get_db() as (conn, cur):
        cur.execute("SELECT * FROM batch_runs ORDER BY started_at DESC LIMIT 1")
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="배치 실행 기록이 없습니다.")
    return _serialize_batch_row(dict(zip(cols, row)))


@app.get("/batch/runs/{run_id}")
async def api_get_batch_run(
    run_id: str = Path(...),
    user: dict = Depends(get_user),
):
    with get_db() as (conn, cur):
        cur.execute("SELECT * FROM batch_runs WHERE id = %s::uuid", (run_id,))
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="배치 실행을 찾을 수 없습니다.")
    return _serialize_batch_row(dict(zip(cols, row)))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
