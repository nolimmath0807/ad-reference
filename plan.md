# 보드 공유 기능

## Overview
보드 소유자가 공유 링크를 생성하면, 링크를 가진 로그인 유저가 해당 보드를 읽기 전용으로 열람할 수 있다. boards 테이블에 share_token 컬럼을 추가하고, 토큰 기반 조회 엔드포인트를 제공한다.

## API 설계
- `POST   /boards/{board_id}/share`   — 공유 토큰 생성 (소유자만, JWT 필수)
- `DELETE /boards/{board_id}/share`   — 공유 토큰 폐기 (소유자만, JWT 필수)
- `GET    /shared/{token}`            — 토큰으로 보드 조회 (JWT 필수, 읽기 전용)

## DB 변경
```sql
ALTER TABLE boards ADD COLUMN share_token VARCHAR(36) UNIQUE;
```

## Key Files
| File | Action | Description |
|------|--------|-------------|
| `backend/migrate.py` | Modify | boards에 share_token 컬럼 추가 |
| `backend/boards/share.py` | Create | 공유 토큰 생성 (소유자 전용) |
| `backend/boards/unshare.py` | Create | 공유 토큰 폐기 |
| `backend/boards/shared_detail.py` | Create | 토큰으로 보드 조회 |
| `backend/api.py` | Modify | 공유 관련 엔드포인트 3개 추가 |
| `frontend/src/types/board.ts` | Modify | share_token 필드 추가 |
| `frontend/src/components/board/ShareBoardDialog.tsx` | Create | 링크 복사 다이얼로그 |
| `frontend/src/components/board/BoardHeader.tsx` | Modify | 공유 버튼 + ShareBoardDialog 연결 |
| `frontend/src/pages/SharedBoardPage.tsx` | Create | 공유 보드 읽기 전용 페이지 |
| `frontend/src/App.tsx` | Modify | /shared/:token 라우트 추가 |

## Implementation Steps
1. **DB 스키마** — migrate.py에 share_token VARCHAR(36) UNIQUE 컬럼 추가
2. **토큰 생성** — share.py: uuid4 토큰 생성 후 boards.share_token에 저장, 소유자 검증
3. **토큰 폐기** — unshare.py: share_token을 NULL로 업데이트
4. **공유 보드 조회** — shared_detail.py: share_token으로 보드 + items 조회
5. **API 라우트** — api.py에 3개 엔드포인트 등록
6. **Frontend 타입** — board.ts에 share_token 추가
7. **ShareBoardDialog** — 링크 생성/복사/공유 중단 UI
8. **BoardHeader** — 공유 버튼 추가, ShareBoardDialog 연결
9. **SharedBoardPage** — 읽기 전용 보드 페이지 (소유자명 + 광고 그리드)
10. **App.tsx** — /shared/:token 라우트 추가

## UX 흐름
1. BoardHeader → "공유" 버튼 클릭
2. ShareBoardDialog → "링크 생성" → POST /boards/{id}/share
3. 링크 복사 버튼 → 클립보드에 /shared/{token} URL 복사
4. 수신자 접속 → SharedBoardPage (읽기 전용)
5. "공유 중단" → DELETE /boards/{id}/share → 토큰 무효화

## Dependencies
- 추가 라이브러리 없음 (uuid 모듈은 Python 내장)

## Risks & Mitigations
- **토큰 추측 공격**: UUID v4 사용으로 충분한 엔트로피 확보
- **소유자 검증 누락**: share.py, unshare.py에서 board.user_id == requester_id 반드시 검증
