import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path as FilePath

from fastapi import FastAPI, Depends, Query, Path, HTTPException
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
# Platforms (JWT required)
# ──────────────────────────────────────────────

@app.get("/platforms/status")
async def api_platforms_status(user: dict = Depends(get_user)):
    platforms = [
        PlatformStatus(
            platform=PlatformType.meta,
            status=Status.active if os.environ.get("META_ACCESS_TOKEN") else Status.unavailable,
            message="Meta Ad Library API 연동" if os.environ.get("META_ACCESS_TOKEN") else None,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
