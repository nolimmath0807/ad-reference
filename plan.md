# Implementation Plan: Ad Reference SaaS (광고 레퍼런스 플랫폼)

## 1. 프로젝트 개요

Meta, Google Ads, TikTok, Instagram의 광고 소재를 수집하여 경쟁사 크리에이티브 레퍼런스를 확보하는 내부 SaaS 웹 애플리케이션. 스니핏(snipit.im)을 레퍼런스로 하여 동일한 UX를 구현한다.

### 핵심 목표

- 멀티 플랫폼 광고 크리에이티브 검색 및 수집
- 키워드/광고주/브랜드 기반 검색 + 고급 필터링
- 개인 보드(컬렉션)에 광고 저장 및 관리
- 광고 상세 정보 (카피, 성과 지표, 집행 기간) 제공
- 유사 광고 추천

### 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | React 19, Vite 7, TypeScript 5.9, Tailwind CSS 4 |
| UI | shadcn/ui (new-york style), Pretendard 폰트 |
| 상태관리 | React Context + useReducer |
| 라우팅 | React Router v7 |
| Backend | Python 3.12, FastAPI, uv 패키지 매니저 |
| DB | Supabase (PostgreSQL) + psycopg2 |
| Auth | JWT (커스텀 구현) |
| 외부 API | Meta Ad Library API, SerpApi (Google), TikTok Commercial Content API |
| 패키지 매니저 | Backend: uv / Frontend: npm |

### 외부 API 전략

| 플랫폼 | API | 비용 | 제한사항 |
|--------|-----|------|---------|
| Meta/Instagram | Meta Ad Library API | 무료 | 공식 API, Facebook + Instagram 광고 모두 커버 |
| Google Ads | SerpApi (Google Ads Transparency Center) | 유료 ($50/월~) | 3rd party, Google 공식 API 없음 |
| TikTok | Commercial Content API | 무료 | 공식이나 EU 데이터만 현재 제공 |

### 프로젝트 구조

```
ad-reference/
├── plan.md              # 프로젝트 계획서 (이 문서)
├── api.yaml             # OpenAPI 3.0 API 명세
├── backend/
│   ├── .env             # 환경변수
│   ├── Dockerfile       # Python 컨테이너
│   ├── api.py           # FastAPI 엔트리포인트
│   ├── conn.py          # DB 연결
│   ├── utils/
│   │   ├── validation.py
│   │   └── auth_helper.py
│   ├── auth/
│   │   ├── model.py
│   │   ├── login.py
│   │   ├── register.py
│   │   └── logout.py
│   ├── ads/
│   │   ├── model.py
│   │   ├── search.py
│   │   ├── detail.py
│   │   └── save.py
│   ├── boards/
│   │   ├── model.py
│   │   ├── create.py
│   │   ├── list.py
│   │   ├── detail.py
│   │   ├── add_item.py
│   │   └── remove_item.py
│   ├── users/
│   │   ├── model.py
│   │   ├── profile.py
│   │   └── update.py
│   └── platforms/
│       ├── model.py
│       ├── meta.py
│       ├── google.py
│       ├── tiktok.py
│       └── scheduler.py
└── frontend/
    ├── .env
    ├── Dockerfile
    └── src/
        ├── components/
        │   ├── ui/          # shadcn/ui 기본 컴포넌트
        │   ├── landing/     # 랜딩 페이지 섹션
        │   ├── auth/        # 로그인/회원가입 폼
        │   ├── dashboard/   # 검색, 필터, 카드
        │   ├── ad/          # 광고 상세, 광고 카드
        │   ├── board/       # 보드 카드, 보드 상세
        │   └── settings/    # 프로필, API, 알림
        ├── pages/
        │   ├── LandingPage.tsx
        │   ├── LoginPage.tsx
        │   ├── RegisterPage.tsx
        │   ├── DashboardPage.tsx
        │   ├── BoardsPage.tsx
        │   ├── BoardDetailPage.tsx
        │   └── SettingsPage.tsx
        ├── contexts/
        │   └── AuthContext.tsx
        ├── lib/
        │   ├── api-client.ts
        │   └── utils.ts
        └── types/
            ├── auth.ts
            ├── ad.ts
            ├── board.ts
            └── user.ts
```

---

## 2. 레이아웃 설계

### 디자인 시스템

| 속성 | 값 |
|------|-----|
| Primary Color | #334FFF (blue) |
| Accent Color | #ec458d (pink) |
| Secondary Color | #6b4cdc (purple) |
| Background | #fff, #fdfdfe |
| Text | #0f172a (dark), #45556c (muted) |
| Card Border Radius | 20px |
| Button (Pill) | border-radius: 9999px |
| Font | Pretendard Variable |

### 2.1 랜딩 페이지

```
+============================================================================+
|  [Logo]  snipit        탐색  기능  요금제  블로그        [로그인] [시작하기] |
+============================================================================+
|                                                                            |
|                         +----- BADGE PILL -----+                           |
|                         | AI 광고 레퍼런스 플랫폼 |                         |
|                         +----------------------+                           |
|                                                                            |
|              찾고 싶을 때 찾아지는 콘텐츠 레퍼런스                           |
|              ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~                      |
|                                                                            |
|         Meta, Google, TikTok, Instagram 광고 크리에이티브를                 |
|         AI가 자동으로 수집하고 정리합니다                                    |
|                                                                            |
|              [====무료로 시작하기====]  [데모 보기 ->]                       |
|              (pill-shaped #334FFF)     (outline pill)                       |
|                                                                            |
|         +----------------------------------------------------------+       |
|         |                                                          |       |
|         |              HERO IMAGE / APP SCREENSHOT                 |       |
|         |          (Dashboard preview with grid cards)              |       |
|         |                                                          |       |
|         +----------------------------------------------------------+       |
|                                                                            |
+----------------------------------------------------------------------------+
|                                                                            |
|                     1,000+         50,000+        4개                       |
|                     광고주 분석     광고 수집      플랫폼 지원               |
|                                                                            |
+----------------------------------------------------------------------------+
|                                                                            |
|              AI로 더 빠르게, 더 정확하게 레퍼런스를 찾으세요                 |
|                                                                            |
|   +------------------+ +------------------+ +------------------+           |
|   | [gradient bg]    | | [gradient bg]    | | [gradient bg]    |           |
|   |  (icon)          | |  (icon)          | |  (icon)          |           |
|   |  멀티 플랫폼     | |  AI 자동 수집    | |  스마트 필터     |           |
|   |  Meta, Google,   | |  키워드 기반     | |  포맷, 성과,    |           |
|   |  TikTok, Insta   | |  자동 크롤링     | |  날짜별 정렬    |           |
|   +------------------+ +------------------+ +------------------+           |
|                                                                            |
|   +------------------+                                                     |
|   | [gradient bg]    |                                                     |
|   |  (icon)          |                                                     |
|   |  개인 보드       |                                                     |
|   |  마음에 드는     |                                                     |
|   |  광고를 저장     |                                                     |
|   +------------------+                                                     |
|                                                                            |
+----------------------------------------------------------------------------+
|                                                                            |
|                   지원 플랫폼 & 연동                                       |
|                                                                            |
|     [Meta Logo]  [Google Logo]  [TikTok Logo]  [Instagram Logo]            |
|                                                                            |
|   +-------------------------------+  +-------------------------------+     |
|   |   "레퍼런스 찾는 시간을       |  |   "경쟁사 광고를 한눈에       |     |
|   |    70% 줄였습니다"            |  |    볼 수 있어서 기획이        |     |
|   |   - 김OO, 퍼포먼스 마케터     |  |    훨씬 빨라졌어요"           |     |
|   +-------------------------------+  +-------------------------------+     |
|                                                                            |
+----------------------------------------------------------------------------+
|                                                                            |
|           지금 바로 경쟁사 광고를 분석해보세요                               |
|           [=======무료로 시작하기=======]                                   |
|                                                                            |
+----------------------------------------------------------------------------+
|  [Logo] snipit          제품  회사  지원       [SNS icons]                  |
|                         이용약관 | 개인정보처리방침                         |
|                         (c) 2026 snipit. All rights reserved.              |
+============================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Navbar | `navbar1` | `shadcnblock/src/blocks/Navbar/navbar1.tsx` |
| Hero | `hero1` | `shadcnblock/src/blocks/Hero/hero1.tsx` |
| Stats | `stats1` | `shadcnblock/src/blocks/Stats/stats1.tsx` |
| Feature Cards | `feature1` / `feature60` | `shadcnblock/src/blocks/Feature/` |
| Platform Integration | `integration1` | `shadcnblock/src/blocks/Integration/integration1.tsx` |
| Testimonials | `testimonial1` / `testimonial4` | `shadcnblock/src/blocks/Testimonial/` |
| CTA | `cta1` | `shadcnblock/src/blocks/Cta/cta1.tsx` |
| Footer | `footer1` | `shadcnblock/src/blocks/Footer/footer1.tsx` |

### 2.2 로그인/회원가입 페이지

```
+============================================================================+
|                          (bg: muted / #fdfdfe)                             |
|                                                                            |
|                     +------- LOGO -------+                                 |
|                     |  [logo-en-blue.svg] |                                |
|                     +--------------------+                                 |
|                                                                            |
|                 +------------------------------+                           |
|                 |         로그인               |                           |
|                 |                              |                           |
|                 |   Email                      |                           |
|                 |   +------------------------+ |                           |
|                 |   |  이메일 주소 입력       | |                           |
|                 |   +------------------------+ |                           |
|                 |                              |                           |
|                 |   Password                   |                           |
|                 |   +------------------------+ |                           |
|                 |   |  ********              | |                           |
|                 |   +------------------------+ |                           |
|                 |                              |                           |
|                 |   [ ] 로그인 상태 유지       |                           |
|                 |                              |                           |
|                 |   [=======로그인=======]     |                           |
|                 |   (full-width, #334FFF)      |                           |
|                 |                              |                           |
|                 |   ---------- 또는 ---------  |                           |
|                 |                              |                           |
|                 |   [G] Google로 계속하기      |                           |
|                 |   (outline button)           |                           |
|                 |                              |                           |
|                 |   비밀번호를 잊으셨나요?     |                           |
|                 |                              |                           |
|                 +------------------------------+                           |
|                                                                            |
|                   계정이 없으신가요? 회원가입 ->                             |
|                                                                            |
+============================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Login Form | `login1` | `shadcnblock/src/blocks/Login/login1.tsx` |
| Signup Form | `signup1` | `shadcnblock/src/blocks/Signup/signup1.tsx` |
| Logo | `logo-en-blue.svg` | `component-hub/logos/logo-en-blue.svg` |

### 2.3 메인 대시보드 / 레퍼런스 검색 (핵심 페이지)

```
+====+===================================================================+
| S  |  HEADER BAR                                                       |
| I  +-------------------------------------------------------------------+
| D  |                                                                   |
| E  |  +--------- SEARCH BAR (full width) ---------+  [Filter] [Sort]  |
| B  |  | (search icon) 키워드, 광고주, 브랜드 검색   |                   |
| A  |  +--------------------------------------------+                   |
| R  |                                                                   |
|    |  PLATFORM TABS                                                    |
| +--+  +------+ +------+ +--------+ +-------+ +-----------+            |
| |  |  | 전체 | | Meta | | Google | |TikTok | |Instagram  |            |
| |Lo|  +------+ +------+ +--------+ +-------+ +-----------+            |
| |go|                                                                    |
| |  |  FILTER BAR                                                       |
| +--+  +--------+ +----------+ +-----------+ +--------+ +----------+   |
| |  |  |포맷  v | |정렬    v | |날짜 범위 v| |업종  v | |성과지표 v|   |
| |탐|  +--------+ +----------+ +-----------+ +--------+ +----------+   |
| |색|                                                                    |
| |  |  RESULTS HEADER                                                   |
| +--+  검색 결과: 12,345건                [Grid/List] [카드 크기 v]     |
| |  |                                                                   |
| |보|  MASONRY GRID OF AD CREATIVE CARDS                                |
| |드|  +-------------+ +-------------+ +-------------+ +-------------+ |
| |  |  | [Thumbnail] | | [Thumbnail] | | [Thumbnail] | | [Thumbnail] | |
| +--+  | /Preview    | | /Preview    | | /Preview    | | /Preview    | |
| |  |  |-------------| |-------------| |-------------| |-------------| |
| |설|  | [Meta icon] | | [TikTok]    | | [Google]    | | [Insta]     | |
| |정|  | Brand Name  | | Brand Name  | | Brand Name  | | Brand Name  | |
| |  |  | [Image] tag | | [Video] tag | | [Carousel]  | | [Reels]     | |
| +--+  | 123 likes   | | 456 likes   | | 789 likes   | | 234 likes   | |
|    |  | [Bookmark]  | | [Bookmark]  | | [Bookmark]  | | [Bookmark]  | |
|    |  +-------------+ +-------------+ +-------------+ +-------------+ |
|    |                                                                   |
|    |  (infinite scroll / load more)                                    |
+====+===================================================================+

SIDEBAR DETAIL (Expanded):
+----------------------------+
|  [logo-en-black.svg]       |
+----------------------------+
|  (search) 탐색             |
|  (bookmark) 보드           |
|  ---- 내 보드 ----         |
|  + 새 보드 만들기          |
|  > 경쟁사 분석             |
|  > 크리에이티브 참고       |
+----------------------------+
|  (settings) 설정           |
|  [Avatar] 사용자명         |
+----------------------------+

SIDEBAR DETAIL (Collapsed):
+------+
|[sym] |  <- symbol.svg
| (ic) |  탐색
| (ic) |  보드
| (ic) |  설정
| [Av] |
+------+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Sidebar | `sidebar` | `shadcn-basic/src/components/ui/sidebar.tsx` |
| Search | `input` + `command` | `shadcn-basic/src/components/ui/` |
| Platform Tabs | `tabs` + `scrollable-tabslist` | `shadcn-basic/` + `shadcnblock/src/components/Scrollable-tabslist/` |
| Filter Dropdowns | `select` + `dropdown-menu` | `shadcn-basic/src/components/ui/` |
| Date Range | `popover` + `calendar` | `shadcn-basic/src/components/ui/` |
| View Toggle | `toggle-group` | `shadcn-basic/src/components/ui/toggle-group.tsx` |
| Ad Card | `card` + `aspect-ratio` + `badge` | `shadcn-basic/src/components/ui/` (커스텀 조합) |
| Loading | `skeleton` | `shadcn-basic/src/components/ui/skeleton.tsx` |
| Logo (expanded) | `logo-en-black.svg` | `component-hub/logos/logo-en-black.svg` |
| Logo (collapsed) | `symbol.svg` | `component-hub/logos/symbol.svg` |

### 2.4 광고 상세 모달

```
+============================================================================+
|  [X Close]                                           AD DETAIL MODAL       |
+============================================================================+
|  +-------------------------------+  +----------------------------------+   |
|  |                               |  |  [Meta icon] [Badge: Image]     |   |
|  |                               |  |  Brand Name / 광고주명          |   |
|  |      LARGE AD PREVIEW         |  |  @advertiser_handle              |   |
|  |      (Image or Video)         |  |                                  |   |
|  |                               |  |  ---- 광고 성과 ----            |   |
|  |                               |  |  +------+ +------+ +------+     |   |
|  |                               |  |  |likes | |cmts  | |shares|     |   |
|  |                               |  |  |1,234 | | 567  | | 89   |     |   |
|  |                               |  |  +------+ +------+ +------+     |   |
|  |                               |  |                                  |   |
|  |                               |  |  ---- 광고 카피 ----            |   |
|  |                               |  |  "광고 카피 텍스트..."          |   |
|  |                               |  |                                  |   |
|  |                               |  |  ---- CTA 버튼 ----             |   |
|  |                               |  |  [지금 구매하기 ->]              |   |
|  +-------------------------------+  |                                  |   |
|                                     |  ---- 집행 기간 ----             |   |
|                                     |  2026.01.15 ~ 2026.02.15        |   |
|                                     |  ---- 태그 ----                  |   |
|                                     |  [이커머스] [뷰티] [할인]       |   |
|                                     |  [======보드에 저장======]       |   |
|                                     |  [  링크 복사  ] [  공유  ]     |   |
|                                     +----------------------------------+   |
+----------------------------------------------------------------------------+
|  비슷한 광고 크리에이티브                                                   |
|  +----------+ +----------+ +----------+ +----------+ +----------+          |
|  | [thumb]  | | [thumb]  | | [thumb]  | | [thumb]  | | [thumb]  |          |
|  +----------+ +----------+ +----------+ +----------+ +----------+          |
+============================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Modal | `dialog` | `shadcn-basic/src/components/ui/dialog.tsx` |
| Preview Image | `aspect-ratio` | `shadcn-basic/src/components/ui/aspect-ratio.tsx` |
| Badges | `badge` | `shadcn-basic/src/components/ui/badge.tsx` |
| Similar Ads | `carousel` | `shadcn-basic/src/components/ui/carousel.tsx` |
| Actions | `button-group-standard-1` | `shadcnblock/src/components/Button-group/` |

### 2.5 보드 목록 페이지

```
+====+===================================================================+
| S  |  내 보드                                        [+ 새 보드 만들기]|
| I  |  +------------------+ +------------------+ +------------------+   |
| D  |  | [Cover Image]    | | [Cover Image]    | | [Cover Image]    |   |
| E  |  | 경쟁사 분석      | | 크리에이티브참고 | | 인스타광고모음  |   |
| B  |  | 12개 저장됨      | | 34개 저장됨     | | 8개 저장됨      |   |
| A  |  | [...menu]        | | [...menu]       | | [...menu]       |   |
| R  |  +------------------+ +------------------+ +------------------+   |
|    |  +------------------+ +- - - - - - - - -+                        |
|    |  | [Cover Image]    | |  + NEW           |                        |
|    |  | TikTok 트렌드    | |  새 보드 만들기   |                        |
|    |  +------------------+ +- - - - - - - - -+                        |
+====+===================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Board Grid | `projects1` | `shadcnblock/src/blocks/Projects/projects1.tsx` |
| Board Card | `card` + `aspect-ratio` | `shadcn-basic/src/components/ui/` |
| New Board Dialog | `dialog` | `shadcn-basic/src/components/ui/dialog.tsx` |
| Dropdown Actions | `dropdown-menu` | `shadcn-basic/src/components/ui/dropdown-menu.tsx` |

### 2.6 보드 상세 페이지

```
+====+===================================================================+
| S  |  [<- 뒤로]  경쟁사 분석                                          |
| I  |  이 보드에는 주요 경쟁사의 Meta, Google 광고를 모아놨습니다        |
| D  |  12개 항목 | 2026.02.20 마지막 수정                                 |
| E  |  [======공유======] [내보내기 v] [수정] [...]                      |
| B  |  +------+ +------+ +--------+ +-------+                          |
| A  |  | 전체 | | Meta | | Google | | TikTok|                          |
| R  |  +------+ +------+ +--------+ +-------+                          |
|    |  +-------------+ +-------------+ +-------------+ +-------------+  |
|    |  | [Thumbnail] | | [Thumbnail] | | [Thumbnail] | | [Thumbnail] |  |
|    |  | [Meta] Br   | | [Google] Br | | [Meta] Br   | | [TikTok]   |  |
|    |  | [Remove]    | | [Remove]    | | [Remove]    | | [Remove]    |  |
|    |  +-------------+ +-------------+ +-------------+ +-------------+  |
+====+===================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Breadcrumb | `breadcrumb` | `shadcn-basic/src/components/ui/breadcrumb.tsx` |
| Tab Filters | `tabs` | `shadcn-basic/src/components/ui/tabs.tsx` |
| Card Grid | `card` + `badge` | `shadcn-basic/src/components/ui/` |
| Actions | `button-group-standard-1` | `shadcnblock/src/components/Button-group/` |
| Remove Confirm | `alert-dialog` | `shadcn-basic/src/components/ui/alert-dialog.tsx` |

### 2.7 설정 페이지

```
+====+===================================================================+
| S  |  설정                                                             |
| I  |  +--------+ +----------+ +----------+ +--------+                 |
| D  |  | 프로필 | | API 설정 | | 알림     | | 요금제 |                 |
| E  |  +--------+ +----------+ +----------+ +--------+                 |
| B  |                                                                   |
| A  |  프로필 정보                                                      |
| R  |  +--------------------------------------------------------+      |
|    |  |  [Avatar] [프로필 사진 변경]                            |      |
|    |  |  이름  [________________]                               |      |
|    |  |  이메일 [________________] (비활성)                     |      |
|    |  |  회사  [________________]                               |      |
|    |  |  직무  [________________ v]                             |      |
|    |  |  [=====변경사항 저장=====]                              |      |
|    |  +--------------------------------------------------------+      |
|    |                                                                   |
|    |  비밀번호 변경                                                    |
|    |  +--------------------------------------------------------+      |
|    |  |  현재 비밀번호 [________________]                       |      |
|    |  |  새 비밀번호 [________________]                         |      |
|    |  |  [=====비밀번호 변경=====]                              |      |
|    |  +--------------------------------------------------------+      |
|    |                                                                   |
|    |  API 키 관리 (API 설정 탭)                                        |
|    |  +--------------------------------------------------------+      |
|    |  |  API Key [sk-xxxx-xxxx] [복사] [재발급]                |      |
|    |  |  사용량: [=========>          ] 12.3%                  |      |
|    |  +--------------------------------------------------------+      |
|    |                                                                   |
|    |  알림 설정 (알림 탭)                                              |
|    |  +--------------------------------------------------------+      |
|    |  |  이메일 알림       [ON]                                 |      |
|    |  |  새 광고 수집 알림  [ON]                                 |      |
|    |  |  주간 리포트       [OFF]                                |      |
|    |  +--------------------------------------------------------+      |
+====+===================================================================+
```

**추천 컴포넌트:**

| 섹션 | 컴포넌트 | 경로 |
|------|----------|------|
| Settings Tabs | `tabs` | `shadcn-basic/src/components/ui/tabs.tsx` |
| Form | `form` + `input` + `label` | `shadcn-basic/src/components/ui/` |
| Select | `select` | `shadcn-basic/src/components/ui/select.tsx` |
| Avatar | `avatar` | `shadcn-basic/src/components/ui/avatar.tsx` |
| Toggle | `switch` | `shadcn-basic/src/components/ui/switch.tsx` |
| Progress | `progress` | `shadcn-basic/src/components/ui/progress.tsx` |
| Delete Confirm | `alert-dialog` | `shadcn-basic/src/components/ui/alert-dialog.tsx` |
| Toast | `sonner` | `shadcn-basic/src/components/ui/sonner.tsx` |

---

## 3. 전체 컴포넌트 인벤토리

### shadcn-basic 사용 목록

| 컴포넌트 | 사용 페이지 |
|----------|------------|
| `alert-dialog` | 보드 상세, 설정 |
| `alert` | 설정 |
| `aspect-ratio` | 대시보드, 광고 상세, 보드 |
| `avatar` | 대시보드, 광고 상세, 설정 |
| `badge` | 랜딩, 대시보드, 광고 상세, 보드 상세 |
| `breadcrumb` | 보드 상세 |
| `button` | 전체 페이지 |
| `calendar` | 대시보드 |
| `card` | 로그인, 대시보드, 광고 상세, 보드, 설정 |
| `carousel` | 광고 상세 |
| `checkbox` | 로그인 |
| `command` | 대시보드 |
| `context-menu` | 보드 |
| `dialog` | 광고 상세, 보드, 보드 상세 |
| `dropdown-menu` | 대시보드, 보드, 보드 상세 |
| `form` | 설정 |
| `hover-card` | 광고 상세 |
| `input` | 로그인, 대시보드, 설정 |
| `label` | 로그인, 설정 |
| `pagination` | 대시보드 |
| `popover` | 대시보드 |
| `progress` | 설정 |
| `scroll-area` | 대시보드 |
| `select` | 대시보드, 설정 |
| `separator` | 로그인, 광고 상세, 보드 상세, 설정 |
| `sheet` | 광고 상세 (대안) |
| `sidebar` | 대시보드, 보드, 보드 상세, 설정 |
| `skeleton` | 대시보드 |
| `sonner` | 설정 |
| `switch` | 설정 |
| `tabs` | 대시보드, 보드 상세, 설정 |
| `toggle-group` | 대시보드 |
| `tooltip` | 대시보드, 광고 상세 |

### shadcnblock 사용 목록

| 블록 | 페이지 |
|------|--------|
| `navbar1` | 랜딩 |
| `hero1` | 랜딩 |
| `stats1` | 랜딩 |
| `feature1` / `feature60` | 랜딩 |
| `integration1` | 랜딩 |
| `testimonial1` / `testimonial4` | 랜딩 |
| `cta1` | 랜딩 |
| `footer1` | 랜딩 |
| `login1` | 로그인 |
| `signup1` | 회원가입 |
| `projects1` | 보드 |
| `scrollable-tabslist` | 대시보드 |
| `button-group-standard-1` | 광고 상세, 보드 상세 |
| `button-group-badges-1` | 대시보드 |
| `badge-outline-1` | 광고 상세 |

### 로고 에셋

| 에셋 | 파일 | 사용처 |
|------|------|--------|
| 컬러 영문 로고 | `logo-en-blue.svg` | 랜딩 Navbar, 로그인/회원가입 |
| 흑백 영문 로고 | `logo-en-black.svg` | 사이드바 (펼침) |
| 심볼 | `symbol.svg` | 사이드바 (접힘), 파비콘 |

---

## 4. 주요 파일 목록

### Backend

| 파일 | 작업 | 설명 |
|------|------|------|
| `backend/.env` | Create | 환경변수 (DATABASE_URL, API keys) |
| `backend/conn.py` | Create | DB 연결 함수 |
| `backend/api.py` | Create | FastAPI 엔트리포인트 |
| `backend/utils/validation.py` | Create | 공통 검증 로직 |
| `backend/utils/auth_helper.py` | Create | JWT 토큰 생성/검증 |
| `backend/auth/model.py` | Create | 인증 Pydantic 모델 |
| `backend/auth/login.py` | Create | 로그인 엔드포인트 |
| `backend/auth/register.py` | Create | 회원가입 엔드포인트 |
| `backend/auth/logout.py` | Create | 로그아웃 엔드포인트 |
| `backend/ads/model.py` | Create | 광고 Pydantic 모델 |
| `backend/ads/search.py` | Create | 광고 검색 (멀티 플랫폼) |
| `backend/ads/detail.py` | Create | 광고 상세 조회 |
| `backend/ads/save.py` | Create | 광고 저장/북마크 |
| `backend/boards/model.py` | Create | 보드 Pydantic 모델 |
| `backend/boards/create.py` | Create | 보드 생성 |
| `backend/boards/list.py` | Create | 보드 목록 조회 |
| `backend/boards/detail.py` | Create | 보드 상세 조회 |
| `backend/boards/add_item.py` | Create | 보드에 광고 추가 |
| `backend/boards/remove_item.py` | Create | 보드에서 광고 제거 |
| `backend/users/model.py` | Create | 사용자 Pydantic 모델 |
| `backend/users/profile.py` | Create | 프로필 조회 |
| `backend/users/update.py` | Create | 프로필 수정 |
| `backend/platforms/model.py` | Create | 플랫폼 응답 모델 |
| `backend/platforms/meta.py` | Create | Meta Ad Library API 연동 |
| `backend/platforms/google.py` | Create | SerpApi (Google Ads) 연동 |
| `backend/platforms/tiktok.py` | Create | TikTok Commercial Content API 연동 |
| `backend/platforms/scheduler.py` | Create | 광고 데이터 자동 수집 스케줄러 |
| `backend/Dockerfile` | Create | Python 컨테이너 |

### Frontend

| 파일 | 작업 | 설명 |
|------|------|------|
| `frontend/.env` | Create | 환경변수 (VITE_API_BASE_URL) |
| `frontend/src/lib/api-client.ts` | Create | API 클라이언트 설정 |
| `frontend/src/lib/utils.ts` | Create | 유틸리티 함수 |
| `frontend/src/types/auth.ts` | Create | 인증 TypeScript 타입 |
| `frontend/src/types/ad.ts` | Create | 광고 TypeScript 타입 |
| `frontend/src/types/board.ts` | Create | 보드 TypeScript 타입 |
| `frontend/src/types/user.ts` | Create | 사용자 TypeScript 타입 |
| `frontend/src/contexts/AuthContext.tsx` | Create | 인증 Context Provider |
| `frontend/src/components/ui/*` | Create | shadcn/ui 기본 컴포넌트 (30+개) |
| `frontend/src/components/landing/*` | Create | 랜딩 페이지 섹션 컴포넌트 |
| `frontend/src/components/auth/*` | Create | 로그인/회원가입 폼 |
| `frontend/src/components/dashboard/*` | Create | 검색바, 필터, 광고 카드 그리드 |
| `frontend/src/components/ad/*` | Create | 광고 카드, 광고 상세 모달 |
| `frontend/src/components/board/*` | Create | 보드 카드, 보드 상세 |
| `frontend/src/components/settings/*` | Create | 프로필, API, 알림 설정 |
| `frontend/src/pages/LandingPage.tsx` | Create | 랜딩/마케팅 페이지 |
| `frontend/src/pages/LoginPage.tsx` | Create | 로그인 페이지 |
| `frontend/src/pages/RegisterPage.tsx` | Create | 회원가입 페이지 |
| `frontend/src/pages/DashboardPage.tsx` | Create | 메인 대시보드 (검색+그리드) |
| `frontend/src/pages/BoardsPage.tsx` | Create | 보드 목록 페이지 |
| `frontend/src/pages/BoardDetailPage.tsx` | Create | 보드 상세 페이지 |
| `frontend/src/pages/SettingsPage.tsx` | Create | 설정 페이지 |
| `frontend/src/App.tsx` | Create | 라우팅 + 레이아웃 |
| `frontend/src/main.tsx` | Create | 앱 엔트리포인트 |
| `frontend/src/index.css` | Create | 글로벌 CSS + Pretendard 폰트 |
| `frontend/Dockerfile` | Create | React 컨테이너 (multi-stage) |

---

## 5. 구현 단계

### Step 1: API 명세 작성
- **에이전트**: `api-yaml-designer`
- OpenAPI 3.0 스펙으로 `api.yaml` 생성
- 엔드포인트: Auth (3), Ads (3), Boards (5), Users (2), Platforms (1)
- 총 14개 API 엔드포인트

### Step 2: Backend 구현
- **에이전트**: `python-coder`
- **Sub-Phase 1 (Foundation)**: .env, conn.py, utils/, 각 서비스 model.py (5-8개 파일, 병렬)
- **Sub-Phase 2 (Platform Integrations)**: meta.py, google.py, tiktok.py, scheduler.py (4개 파일, 병렬)
- **Sub-Phase 3 (Endpoints)**: auth/, ads/, boards/, users/ 전체 (12개 파일, 병렬)
- **Sub-Phase 4 (Entry Point)**: api.py + 통합 테스트

### Step 3: Frontend 구현
- **에이전트**: `frontend-coder`
- **Sub-Phase 1 (Foundation)**: .env, api-client, types, contexts, index.css (7-8개 파일, 병렬)
- **Sub-Phase 1.5 (Common UI)**: shadcn 컴포넌트 설치 + 커스텀 UI 컴포넌트 (AdCard, FilterBar 등)
- **Sub-Phase 2 (Pages)**: 7개 페이지 + 기능별 컴포넌트 (15-20개 파일, 병렬)
- **Sub-Phase 3 (Integration)**: App.tsx 라우팅, 통합 테스트

### Step 4: 컨테이너화
- **에이전트**: `python-coder`
- Backend Dockerfile + Frontend Dockerfile + docker-compose.yml

---

## 6. 의존성

### Backend
- fastapi
- uvicorn
- psycopg2-binary
- python-dotenv
- pydantic
- pyjwt
- httpx (외부 API 호출)
- apscheduler (스케줄링)

### Frontend
- react, react-dom
- react-router-dom
- @radix-ui/* (shadcn 의존성)
- class-variance-authority
- clsx, tailwind-merge
- lucide-react
- react-masonry-css (또는 CSS columns)
- react-intersection-observer (무한 스크롤)
- date-fns
- embla-carousel-react (carousel)

### 외부 서비스
- Supabase (PostgreSQL)
- Meta Ad Library API (무료, 개발자 앱 등록 필요)
- SerpApi (유료, API 키 필요)
- TikTok Commercial Content API (무료, 개발자 계정 + 승인 필요)

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| TikTok API EU 데이터 제한 | 한국 광고 데이터 부재 | TikTok 탭에 "EU 데이터만 제공" 안내, 추후 확대 시 대응 |
| SerpApi 비용 | 월 $50~ 운영비 | 캐싱 + rate limiting으로 API 호출 최소화 |
| Meta API 접근 토큰 만료 | 데이터 수집 중단 | 토큰 자동 갱신 로직 구현 |
| Masonry 레이아웃 성능 | 대량 카드 렌더링 지연 | 가상화 (react-window) + 무한 스크롤 페이지네이션 |
| 광고 이미지 저장/캐싱 | 스토리지 비용 증가 | Supabase Storage 활용, 썸네일만 저장 |
