# 다시, 공간

대구광역시의 유휴시설을 청년 창업가, 예술가, 소상공인과 연결하는 추천·매칭 웹 서비스입니다.

기획 근거는 `ppt/` 폴더의 다음 문서입니다.

- `ppt/다시_공간_중간발표.pptx`
- `ppt/다시_공간_중간발표_D-7_할일배분반영.pptx`

> 이 문서는 **현재 로컬 작업 디렉토리에 실제로 있는 코드** 기준으로 작성했습니다. `origin/main`에는 아직 로컬로 pull하지 않은 커밋 3개(`project/backend/`, `project/data_pipeline/` FastAPI 백엔드 추가분)가 더 있고, 해당 부분은 별도로 표시했습니다.

## Overview

- 공간 탐색 / 지도 / 맞춤 추천 / 관심 공간 저장 / 방문·이용 신청 / 운영센터(관리자) 화면을 제공하는 매칭 웹앱
- 프론트엔드는 순수 정적 파일(`index.html` + `app.js` + `styles.css`)이며, 프레임워크 없이 바닐라 JS로 작성됨
- 데이터는 **API 우선, 실패 시 번들 데이터로 폴백** 구조: `app.js`가 `/api/v1/spaces`, `/api/v1/common-codes`를 먼저 호출하고, 실패하면 `data.js`에 하드코딩된 목업 데이터(`INITIAL_SPACES`, `COMMON_CODES`)를 대신 씀
- 사용자가 브라우저에서 변경한 값(관심 공간, 신청 내역, 관리자가 바꾼 공간 상태)은 `localStorage`에 저장되어 새로고침해도 유지됨
- 지도는 기본적으로 Leaflet + OpenStreetMap(무료, 키 불필요). 카카오 로드뷰 기능만 백엔드 `/api/v1/config`에서 받은 JS 키로 카카오맵 SDK를 동적 로드해서 씀
- 백엔드(FastAPI + PostgreSQL)는 팀원이 `origin/main`에 이미 올려둔 상태이며, 로컬에는 아직 pull 전이라 존재하지 않음 (아래 "백엔드(원격)" 항목 참고)

## 디렉토리 구조

### 로컬에 실제로 있는 것

```text
DIP_PYTHON_PROJECT/
├── .gitattributes
├── README.md
├── index.html            # 화면 구조 (탐색 / 지도 / 추천 / 관심공간 / 신청 / 관리자 모달)
├── styles.css             # 디자인 시스템, 반응형 레이아웃
├── data.js                # 번들 목업 데이터: INITIAL_SPACES(12건), COMMON_CODES, INITIAL_DATA_SYNC_LOGS
├── app.js                 # 상태 관리, 렌더링, 추천 점수, 지도, 신청/즐겨찾기, 관리자 기능
└── ppt/
    ├── 다시_공간_중간발표.pptx
    └── 다시_공간_중간발표_D-7_할일배분반영.pptx
```

### 백엔드 (`origin/main`에는 있음, 로컬은 아직 pull 전)

`git fetch` 기준으로 원격에는 아래 구조가 추가돼 있습니다. `git pull`로 받아야 로컬에 생깁니다.

```text
project/
├── backend/                         # FastAPI 애플리케이션
│   ├── main.py                      # 앱 진입점, 라우터 등록, /health, /api/v1/config/public
│   ├── config.py                    # .env 기반 설정
│   ├── database.py                  # DB 엔진/세션, 초기 스키마 생성, seed 적재
│   ├── models.py / schemas.py       # SQLAlchemy 모델 / Pydantic 스키마
│   ├── security.py                  # 비밀번호 해시, JWT
│   ├── recommendation.py            # 추천 점수 계산 (서버 버전)
│   ├── seed_spaces.json             # 시연용 샘플 공간 데이터 6건
│   ├── routers/                     # auth, users, spaces, favorites, applications, recommendations, admin
│   ├── migrations/                  # Alembic
│   └── tests/
└── data_pipeline/                   # 원천 CSV → DB 반영 스크립트
    ├── sample_raw.csv
    ├── clean_spaces.py
    ├── import_spaces.py
    └── spaces_import_template.csv
```

**주의**: 원격 커밋에는 `index.html`/`app.js`/`styles.css`/`data.js`가 레포에서 삭제되어 있고, `project/` 아래에도 다시 추가되지 않았습니다. `pull` 하면 지금 로컬에서 작업 중인 프론트 파일들과 충돌(수정/삭제 충돌)이 날 수 있으니, pull 전에 커밋해두고 병합 시 프론트 파일을 `project/` 아래로 옮길지 팀원과 맞춰야 합니다.

## 실행 방법

### 지금 로컬 상태 그대로 (백엔드 없이, 프론트만)

```bash
python -m http.server 8000
```

브라우저에서 `http://localhost:8000`을 엽니다. 백엔드가 없으므로 `/api/v1/*` 호출은 전부 실패하고, `app.js`가 자동으로 `data.js`의 번들 데이터로 대체해서 보여줍니다. 카카오 로드뷰는 `/api/v1/config`를 못 받아오므로 동작하지 않고, 나머지 기능(탐색/추천/즐겨찾기/신청/관리자)은 `localStorage` 기반으로 정상 동작합니다.

### 백엔드까지 pull해서 풀스택으로 띄우는 경우

```bash
git pull origin main
cd project
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
# project/backend/.env 에 DATABASE_URL, JWT_SECRET 등 설정 (project/backend/config.py 참고)
uvicorn backend.main:app --reload --port 8001
```

`http://localhost:8001`로 접속하면 `app.js`가 `/api/v1/spaces` 등을 정상적으로 받아와 PostgreSQL 데이터로 렌더링합니다. (단, 위 "주의"에 적은 대로 프론트 파일 위치를 먼저 맞춰야 함.)

### 데이터 업데이트 방법

- **지금 로컬 상태(백엔드 없음)**: 데이터 수정은 `data.js`의 `INITIAL_SPACES` 배열을 직접 편집하는 방식뿐입니다. 별도 파이프라인 스크립트는 로컬에 없습니다. 화면의 "공공데이터 동기화 ↻" 버튼(`app.js`의 `simulateDataSync()`)은 실제로 아무 데이터도 갱신하지 않는 UI 목업입니다 (1.2초 대기 후 토스트 메시지만 띄움).
- **백엔드 pull 후**: `project/data_pipeline/clean_spaces.py`로 원본 CSV를 정제하고, `project/data_pipeline/import_spaces.py --commit`으로 PostgreSQL에 반영합니다. 자세한 내용은 아래 "데이터 파이프라인 설명" 참고.

## 데이터 출처

- **현재 로컬 데이터는 전부 수기로 작성한 목업입니다.** `data.js`의 `INITIAL_SPACES` 12건은 실제 공공 API에서 받아온 데이터가 아니라, 대구 9개 구·군을 커버하도록 사람이 직접 만든 예시 데이터입니다.
- `data.js`의 `INITIAL_DATA_SYNC_LOGS`(대구 공공데이터 포털 API, 도시재생 웹 크롤러 등을 언급하는 로그 3건)도 **화면에 실제로 쓰이지 않는 죽은 데이터**입니다(`app.js` 어디에서도 참조하지 않음). "이런 식으로 연동될 예정"이라는 기획 의도만 남긴 플레이스홀더로 보입니다.
- vworld, data.go.kr 같은 실제 정부·공공 API 엔드포인트를 호출하는 코드는 로컬에도, 원격(`origin/main`)에도 없습니다. 원격 `project/data_pipeline/clean_spaces.py`의 주석에 "외부 데이터 확보 후 확장 항목: 대구 공공데이터 API 실제 호출, 필요 시 지오코딩 연동"이라고 **TODO로만** 적혀 있고, 실제 호출 코드는 아직 구현되지 않았습니다.
- 즉 지금 시점에서 "데이터 출처"는 사실상 없고, 전부 시연/개발용 샘플 데이터입니다.

## 데이터 파이프라인 설명 (함수 단위)

### 지금 로컬 프론트엔드가 실제로 하는 일

```
index.html 로드
  → DOMContentLoaded 이벤트 → init()                         [app.js:36]
      → loadState()                                          [app.js:57]
          1) fetchJSON('/api/v1/spaces')                      [app.js:51]
             실패 시 catch에서 경고 로그만 남기고 apiSpaces = null
          2) fetchJSON('/api/v1/common-codes')
             실패 시 COMMON_CODES는 data.js 번들 값 그대로 사용
          3) readStorage(STORAGE.spaces, apiSpaces || INITIAL_SPACES)  [app.js:84]
             - localStorage에 저장된 값이 있으면 그걸 최우선으로 사용
             - 없으면 (API 데이터 → 없으면 data.js의 INITIAL_SPACES) 순으로 fallback
             → appState.spaces 로 확정
          4) readStorage(STORAGE.favorites, []), readStorage(STORAGE.applications, [])
             → appState.favorites / appState.applications 로 확정
      → populateOptions(), renderDistrictChips(), renderFeatured(), renderCatalog(),
        renderDistrictStats(), renderFavorites(), bindEvents(), initMap(),
        setMinimumVisitDate()  → 화면 렌더링
```

- `fetchJSON(path)` [app.js:51]: `fetch()` 래퍼. HTTP 에러면 예외를 던짐 → 호출부에서 `try/catch`로 잡아 폴백 처리.
- `readStorage(key, fallback)` [app.js:84]: `localStorage.getItem(key)`를 JSON 파싱, 없거나 파싱 실패하면 `fallback` 반환.
- `saveState(key)` [app.js:94]: `appState`의 해당 부분(`favorites`/`spaces`/`applications`)을 다시 `localStorage`에 직렬화해서 저장. 아래 지점에서 호출됨.
  - `toggleFavorite(id)` [app.js:425] → `saveState(STORAGE.favorites)`
  - `submitApplication(event)` [app.js:584] → `saveState(STORAGE.applications)`
  - `updateSpaceStatus(id, status)` [app.js:757] (관리자가 공간 상태 변경) → `saveState(STORAGE.spaces)`

### 신청서 제출 흐름

```
submitApplication(event)                                     [app.js:584]
  → POST /api/v1/applications 시도
      성공: 서버가 준 application 객체 사용
      실패(catch): "이 기기에만 남깁니다" 경고 로그, 로컬 임시 id(APP-<timestamp>)로 대체
  → appState.applications.unshift(application)
  → saveState(STORAGE.applications)
```

### 맞춤 추천 점수 계산 (서버 API 호출 없이 클라이언트에서 직접 계산)

```
submitRecommendation(event)                                   [app.js:618]
  입력: 희망 지역/용도/예산/면적/주차 여부 (recommendCriteria)
  appState.spaces 각 항목에 대해:
    기본 15점
    + 지역 일치(또는 전체) 25점
    + 용도 일치 30점
    + 예산 이내 20점 (예산+10만원 이내면 8점)
    + 최소 면적 충족 10점
    + 주차 필요&가능 8점 / 주차 불필요면 5점
    → 최대 98점으로 clamp, 점수 내림차순 정렬 후 상위 3건 표시
```
이 가중치(15/25/30/20/10/8/5)는 원격 `project/backend/recommendation.py`의 서버 버전 로직과 동일한 값입니다. 다만 지금 로컬 프론트는 서버를 호출하지 않고 **클라이언트에서 직접** 계산합니다.

### 관리자 "공공데이터 동기화" 버튼 (실제 파이프라인 아님)

```
simulateDataSync()                                             [app.js:769]
  버튼 비활성화 → "데이터 확인 중…" 표시
  → setTimeout 1.2초
  → 버튼 원복 + toast("대구시 공공데이터 60건을 확인했습니다.")
  (appState나 localStorage는 전혀 건드리지 않음 — 순수 UI 연출)
```

### 백엔드 pull 이후의 실제 파이프라인 (원격 코드 기준, 로컬엔 아직 없음)

```
원본 CSV (project/data_pipeline/sample_raw.csv 또는 실제 수집 CSV)
  ↓ clean_spaces.py: clean_row() / normalize_text() / parse_number()
    - 공백·주소 정규화, "142.5㎡"/"35만원" 같은 문자열 → 숫자 변환
    - 용도·상태 문자열 → 공통 코드 매핑 (CATEGORY_CODES / STATUS_CODES)
    - clean_file(): 이름+주소 기준 중복 제거, 필수값 누락 행은 rejected로 분리
  ↓ (정제 결과를 project/data_pipeline/spaces_import_template.csv 컬럼 형식으로 사람이 보강: id, deposit, lat, lng, images 등)
  ↓ import_spaces.py: parse_row() → SpaceCreate(Pydantic) 검증
    - load_and_validate(): id 중복 등 오류는 라인 번호와 함께 리포트, 기본은 dry-run
    - upsert(): --commit 플래그가 있을 때만 SQLAlchemy로 PostgreSQL Space/SpaceImage 테이블에 반영
    - 실행 결과를 DataSyncLog에 기록
  ↓
PostgreSQL → backend/database.py: seed_spaces() 또는 routers/spaces.py API 조회
  → 프론트(app.js)의 fetchJSON('/api/v1/spaces')가 받아서 렌더링
```
