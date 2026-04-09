# Featured References (추천 레퍼런스) 구현 계획

## Overview
관리자가 좋은 레퍼런스라고 판단한 광고를 큐레이션하여 별도 페이지에서 보여주는 기능. 관리자는 광고 상세 모달/그리드에서 "추천 레퍼런스"로 등록하고, 일반 사용자는 큐레이션된 광고만 모아볼 수 있음.

## Layout Design

```
┌─────────────────────────────────────────────────────────┐
│ [Sidebar]  │  Featured References                [+ Add] │
│            │─────────────────────────────────────────────│
│  Dashboard │  [All] [Google] [Meta]    [Search...] [Sort]│
│            │─────────────────────────────────────────────│
│  Ads       │                                             │
│  Boards    │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│ ★Featured  │  │ thumbnail│ │ thumbnail│ │ thumbnail│     │
│  Settings  │  │ ─────── │ │ ─────── │ │ ─────── │      │
│            │  │ brand   │ │ brand   │ │ brand   │      │
│            │  │ format  │ │ format  │ │ format  │      │
│            │  │ [Remove]│ │ [Remove]│ │ [Remove]│      │
│            │  └─────────┘ └─────────┘ └─────────┘      │
│            │                                             │
│            │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│            │  │ thumbnail│ │ thumbnail│ │ thumbnail│     │
│            │  │ ...     │ │ ...     │ │ ...     │      │
│            │  └─────────┘ └─────────┘ └─────────┘      │
│            │                                             │
│            │          [ Load More ]                      │
└─────────────────────────────────────────────────────────┘
```

- **[+ Add]**: 관리자 전용, 기존 광고 검색 → 추천에 추가
- **[Remove]**: 관리자 전용, 추천에서 제거 (광고 자체 삭제 아님)
- 기존 AdGrid/AdCard 컴포넌트 재사용
- 플랫폼 탭, 검색, 정렬 필터 지원

## DB Schema

```sql
CREATE TABLE IF NOT EXISTS featured_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ad_id UUID NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    memo TEXT,
    UNIQUE(ad_id)
);
CREATE INDEX idx_featured_references_added_at ON featured_references(added_at DESC);
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/featured-references` | 로그인 | 추천 광고 목록 (페이지네이션, 플랫폼 필터) |
| `POST` | `/admin/featured-references` | 관리자 | 광고를 추천에 추가 (ad_id, memo) |
| `DELETE` | `/admin/featured-references/{ad_id}` | 관리자 | 추천에서 제거 |

## Key Files

| File | Action | Description |
|------|--------|-------------|
| `backend/migrate.py` | Modify | `featured_references` 테이블 생성 마이그레이션 추가 |
| `backend/featured/add.py` | Create | POST /admin/featured-references (광고 추천 등록) |
| `backend/featured/remove.py` | Create | DELETE /admin/featured-references/{ad_id} (추천 해제) |
| `backend/featured/list.py` | Create | GET /featured-references (추천 목록 조회 + 필터) |
| `backend/featured/model.py` | Create | Pydantic 모델 |
| `backend/api.py` | Modify | 라우트 3개 추가 |
| `frontend/src/pages/FeaturedPage.tsx` | Create | 추천 레퍼런스 페이지 |
| `frontend/src/components/featured/AddFeaturedModal.tsx` | Create | 광고 검색 → 추천 추가 모달 |
| `frontend/src/App.tsx` | Modify | 라우트 추가 |
| `frontend/src/components/layout/AppSidebar.tsx` | Modify | 사이드바 메뉴 추가 |

## Implementation Steps

### Phase 1: Foundation (병렬)
- Task 1-1: `backend/migrate.py` 수정 — featured_references 테이블 마이그레이션 추가 → agent: python-coder
- Task 1-2: `backend/featured/model.py` 생성 — Pydantic 모델 (FeaturedReferenceCreate, FeaturedReferenceResponse) → agent: python-coder

### Phase 2: Backend Endpoints (병렬)
- Task 2-1: `backend/featured/add.py` 생성 — POST 추천 등록 로직 → agent: python-coder
- Task 2-2: `backend/featured/remove.py` 생성 — DELETE 추천 해제 로직 → agent: python-coder
- Task 2-3: `backend/featured/list.py` 생성 — GET 추천 목록 조회 (필터, 페이지네이션) → agent: python-coder
- Task 2-4: `backend/api.py` 수정 — 라우트 3개 연결 → agent: python-coder

### Phase 3: Frontend (병렬)
- Task 3-1: `frontend/src/pages/FeaturedPage.tsx` 생성 — 추천 레퍼런스 페이지 → agent: frontend-coder
- Task 3-2: `frontend/src/components/featured/AddFeaturedModal.tsx` 생성 — 광고 검색 추가 모달 → agent: frontend-coder
- Task 3-3: `frontend/src/App.tsx` 수정 — 라우트 추가 → agent: frontend-coder
- Task 3-4: `frontend/src/components/layout/AppSidebar.tsx` 수정 — 사이드바 메뉴 추가 → agent: frontend-coder

## Dependencies
- 기존 ads 테이블, users 테이블
- 기존 AdGrid, AdCard, FilterBar, PlatformTabs 프론트엔드 컴포넌트
- get_admin_user() FastAPI dependency

## Risks & Mitigations
- **기존 AdCard 재사용**: Remove 버튼 추가 시 optional prop으로 처리
- **광고 삭제 시 연쇄**: ON DELETE CASCADE로 자동 처리
