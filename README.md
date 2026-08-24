# 다시, 공간

대구광역시의 유휴시설을 청년 창업가, 예술가, 소상공인과 연결하는 추천·매칭 웹 서비스입니다. 프론트엔드(정적 페이지)와 FastAPI + PostgreSQL 백엔드가 `project/` 한 폴더 안에 함께 있고, 서버 프로세스 하나(`uvicorn`)로 같이 뜹니다.

## Overview

- 공간 탐색 / 지도 / 맞춤 추천 / 관심 공간 저장 / 방문·이용 신청 / 운영센터(관리자) 화면을 제공하는 매칭 웹앱
- **프론트+백엔드 단일 서버**: `project/backend/main.py`가 `project/index.html` / `project/app.js` / `project/styles.css`를 `FileResponse`로 직접 서빙. 별도 프론트 서버, CORS 설정 불필요
- 데이터는 **API 우선, 실패 시 번들 데이터로 폴백** 구조: `app.js`가 `/api/v1/spaces`, `/api/v1/common-codes`를 먼저 호출하고, 실패하면 `data.js`에 하드코딩된 목업 데이터(`INITIAL_SPACES`, `COMMON_CODES`)를 대신 씀
- 인증은 JWT 기반, 역할은 일반 사용자와 관리자(admin)로 구분
- 추천 점수는 지역·용도·예산·면적·주차 가중치 규칙 기반(현재 프론트는 클라이언트에서 직접 계산, 백엔드에도 동일 로직이 별도로 존재 — 아래 참고)
- 지도는 기본 Leaflet + OpenStreetMap(무료, 키 불필요). 카카오 로드뷰만 백엔드 `/api/v1/config`에서 받은 JS 키로 카카오맵 SDK를 동적 로드
- 사용자가 브라우저에서 변경한 값(관심 공간, 신청 내역, 관리자가 바꾼 공간 상태)은 `localStorage`에도 저장되어 새로고침해도 유지됨

## 디렉토리 구조

```text
DIP_PYTHON_PROJECT/
└── project/
    ├── .env                              # 로컬 환경변수 (git 미추적)
    ├── .gitignore
    ├── index.html, styles.css, app.js, data.js   # 프론트엔드. main.py가 이 경로(PROJECT_DIR)를 FileResponse로 서빙
    ├── backend/                          # FastAPI 애플리케이션
    │   ├── main.py                       # 앱 진입점 + 프론트엔드/API 라우터 등록, /health, /config/public
    │   ├── config.py                     # .env 기반 설정 (Settings, env_file = project/.env)
    │   ├── database.py                   # DB 엔진, 세션, 초기 스키마 생성, seed 적재
    │   ├── models.py                     # SQLAlchemy ORM 모델
    │   ├── schemas.py                    # Pydantic 요청/응답 스키마
    │   ├── security.py                   # 비밀번호 해시, JWT 발급/검증
    │   ├── dependencies.py               # 인증/권한 의존성
    │   ├── recommendation.py             # 추천 점수 계산 로직 (서버 버전)
    │   ├── seed_spaces.json              # 시연용 샘플 공간 데이터 6건 (앱 시작 시 자동 적재)
    │   ├── requirements.txt
    │   ├── routers/
    │   │   ├── auth.py                   # 회원가입 / 로그인
    │   │   ├── users.py                  # 내 정보, 마이페이지 선호 설정
    │   │   ├── spaces.py                 # 공간 목록/상세
    │   │   ├── favorites.py              # 관심 공간
    │   │   ├── applications.py           # 이용 신청
    │   │   ├── recommendations.py        # 맞춤 추천, 적합도 점수
    │   │   └── admin.py                  # 관리자: 신청 검토, 공간 관리, 동기화 로그
    │   ├── migrations/                   # Alembic 스키마 버전 관리
    │   │   └── versions/
    │   └── tests/                        # pytest API 테스트
    └── data_pipeline/                    # 원천 데이터 → DB 반영 파이프라인
        ├── sample_raw.csv                # 정제 전 원본 예시 데이터
        ├── clean_spaces.py               # 1차 정제 스크립트
        ├── import_spaces.py              # 정제된 CSV를 검증 후 DB에 upsert
        └── spaces_import_template.csv    # 실제 데이터 입력 시 따라야 할 컬럼 양식
```

> 이전에 루트에 있던 `ppt/` 기획 문서(pptx 2개)는 팀원 커밋에서 레포째로 삭제되어 이 브랜치에도 반영되어 있지 않습니다(의도적으로 삭제 반영함).

## 실행 방법

### 1. 준비

```bash
cd project
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

PostgreSQL이 미리 떠 있어야 합니다. `AUTO_CREATE_TABLES=true`(기본값)면 서버 최초 실행 시 테이블과 seed 데이터가 자동 생성됩니다.

### 2. 환경 변수 / API 키 설정

`project/.env` 파일을 만듭니다 (`backend/config.py`의 `Settings` 기준 — `env_file`이 `project/.env`를 가리킵니다. `backend/.env`가 아님에 주의).

```env
# 필수
DATABASE_URL=postgresql+psycopg://dasi_space:dasi_space@localhost:5433/dasi_space
JWT_SECRET=change-this-secret

# 같은 서버에서 프론트를 서빙하므로 기본값 그대로 두면 됨.
# 프론트를 별도 dev 서버로 띄울 때만 그 주소를 추가.
CORS_ORIGINS=http://localhost:8001,http://127.0.0.1:8001
ALLOWED_HOSTS=*

# 지도 API 키 (선택) — 비워두면 자동으로 Leaflet(무료 지도)로 대체됨
KAKAO_MAP_APP_KEY=

# 선택: 서버 최초 기동 시 관리자 계정 자동 생성 (둘 다 채워야 동작, 비밀번호 8자 이상)
BOOTSTRAP_ADMIN_EMAIL=
BOOTSTRAP_ADMIN_PASSWORD=
```

**카카오맵 API 키 발급 및 도메인 등록**

`KAKAO_MAP_APP_KEY`를 설정하면 `/api/v1/config`가 카카오 JS 키를 반환하고 프론트가 카카오맵 SDK로 로드뷰를 그립니다. 키를 비워두면 로드뷰만 비활성화되고 메인 지도(Leaflet)는 그대로 동작합니다.

1. [Kakao Developers](https://developers.kakao.com)에서 애플리케이션 생성
2. "앱 키" 중 **JavaScript 키**를 복사해 `.env`의 `KAKAO_MAP_APP_KEY`에 붙여넣기
3. 앱 설정 → **플랫폼 → Web 플랫폼 등록**에서 실제 서비스 도메인을 등록 (예: `http://localhost:8001`, 배포 시 실제 도메인)
   - 이 등록이 없으면 JS SDK가 도메인 불일치로 로드뷰를 로드하지 않음(인증 실패)
   - 로컬 개발 포트를 바꾸면 등록 도메인도 같이 갱신해야 함
4. 서버를 재시작하면 반영됨 (`.env`는 앱 기동 시 1회 로드)

### 3. 서버 띄우기

```bash
cd project
uvicorn backend.main:app --reload --port 8001
```

- `http://localhost:8001` : 프론트엔드(`index.html`)
- `http://localhost:8001/health` : 서버·DB 상태 확인
- `http://localhost:8001/docs` : FastAPI 자동 생성 API 문서

### 4. 데이터 업데이트 방법

정식 공간 데이터를 추가/갱신할 때는 `seed_spaces.json`이나 `data.js`를 직접 고치지 않고 아래 파이프라인을 사용합니다.

```bash
cd project/data_pipeline

# 1) 원본 CSV 정제 (공백/주소 정리, 숫자 변환, 공통 코드 매핑, 중복 제거)
python clean_spaces.py --input sample_raw.csv --output cleaned_preview.json

# 2) 정제 결과를 spaces_import_template.csv 양식에 맞춰 최종 CSV로 정리한 뒤 검증(dry-run)
python import_spaces.py my_spaces.csv

# 3) 검증 통과 시 실제 DB 반영
python import_spaces.py my_spaces.csv --commit
```

- `clean_spaces.py`는 검증/정제 미리보기만 만들고 DB에 쓰지 않습니다.
- `import_spaces.py`는 `--commit`을 붙이지 않으면 항상 dry-run(검증만)이며, 성공/실패 건수와 오류 라인을 출력합니다.
- 각 실행은 `DataSyncLog`(관리자 화면의 동기화 로그)에 기록됩니다.
- 화면의 "공공데이터 동기화 ↻" 버튼(`app.js`의 `simulateDataSync()`)은 이 파이프라인과 **무관한 UI 목업**입니다. 1.2초 대기 후 토스트만 띄우고 실제로는 아무 데이터도 갱신하지 않습니다.

## 데이터 출처

- **현재 상태: 전부 시연/개발용 샘플 데이터입니다.** 실제 외부 API로 수집된 데이터가 아닙니다.
  - 백엔드 최초 실행 시 `project/backend/seed_spaces.json`(공간 6건, `source_name: "프로젝트 시연 샘플"`)이 자동 적재됨
  - 프론트 번들 `project/data.js`의 `INITIAL_SPACES`(12건)는 API 실패 시 폴백용으로 쓰이는, 사람이 직접 작성한 예시 데이터
  - 두 데이터셋(6건 vs 12건)은 서로 다른 별개의 샘플이며 아직 하나로 합쳐지지 않았습니다 — 정식 데이터 반영 시 정리 필요
- `data.js`의 `INITIAL_DATA_SYNC_LOGS`(대구 공공데이터 포털 API, 도시재생 웹 크롤러 등을 언급하는 로그 3건)는 화면 어디에서도 실제로 참조되지 않는 **죽은 데이터**입니다. "이런 식으로 연동될 예정"이라는 기획 의도만 남긴 플레이스홀더로 보입니다.
- `project/data_pipeline/sample_raw.csv`도 수기로 작성한 예시 원본이며, 실 데이터가 아닙니다.
- `clean_spaces.py` 주석에 명시된 향후 계획(미구현, TODO):
  - 대구 공공데이터포털(data.go.kr) 등 공공데이터 API 실제 호출
  - VWorld 등 좌표계/주소 기반 지오코딩 연동 (주소만 있는 행의 위경도 보완)
  - 필요 시 허용된 대상 한정 수집기 추가
- 즉, 현재 코드베이스에는 vworld·정부 API 엔드포인트로 실제 연동된 코드는 없습니다. `spaces_import_template.csv`의 `source_name`, `source_url` 컬럼에 실제 데이터를 넣을 때 출처를 기록하도록 양식만 준비된 상태입니다.
- `main.py`의 `/health` 응답 `todo` 목록에도 `public_data_source`가 남아 있어, 공공데이터 연동이 아직 완료되지 않았음을 코드 상에서도 확인할 수 있습니다.

## 데이터 파이프라인 설명 (함수 단위)

### 프론트엔드가 초기 데이터를 불러오는 흐름

```
index.html 로드
  → DOMContentLoaded 이벤트 → init()                         [app.js]
      → loadState()
          1) fetchJSON('/api/v1/spaces')
             실패 시 catch에서 경고 로그만 남기고 apiSpaces = null
          2) fetchJSON('/api/v1/common-codes')
             실패 시 COMMON_CODES는 data.js 번들 값 그대로 사용
          3) readStorage(STORAGE.spaces, apiSpaces || INITIAL_SPACES)
             - localStorage에 저장된 값이 있으면 그걸 최우선으로 사용
             - 없으면 (API 데이터 → 없으면 data.js의 INITIAL_SPACES) 순으로 fallback
             → appState.spaces 로 확정
          4) readStorage(STORAGE.favorites, []), readStorage(STORAGE.applications, [])
             → appState.favorites / appState.applications 로 확정
      → populateOptions(), renderDistrictChips(), renderFeatured(), renderCatalog(),
        renderDistrictStats(), renderFavorites(), bindEvents(), initMap(),
        setMinimumVisitDate()  → 화면 렌더링
```

- `fetchJSON(path)`: `fetch()` 래퍼. HTTP 에러면 예외를 던짐 → 호출부에서 `try/catch`로 잡아 폴백 처리.
- `readStorage(key, fallback)`: `localStorage.getItem(key)`를 JSON 파싱, 없거나 파싱 실패하면 `fallback` 반환.
- `saveState(key)`: `appState`의 해당 부분(`favorites`/`spaces`/`applications`)을 다시 `localStorage`에 직렬화해서 저장. 아래 지점에서 호출됨.
  - `toggleFavorite(id)` → `saveState(STORAGE.favorites)`
  - `submitApplication(event)` → `saveState(STORAGE.applications)`
  - `updateSpaceStatus(id, status)` (관리자가 공간 상태 변경) → `saveState(STORAGE.spaces)`

### 신청서 제출 흐름

```
submitApplication(event)
  → POST /api/v1/applications 시도
      성공: 서버가 준 application 객체 사용
      실패(catch): "이 기기에만 남깁니다" 경고 로그, 로컬 임시 id(APP-<timestamp>)로 대체
  → appState.applications.unshift(application)
  → saveState(STORAGE.applications)
```
백엔드 쪽은 `routers/applications.py`가 같은 요청을 받아 PostgreSQL에 저장합니다.

### 맞춤 추천 점수 계산

```
submitRecommendation(event)                                   [app.js, 프론트]
  입력: 희망 지역/용도/예산/면적/주차 여부
  appState.spaces 각 항목에 대해:
    기본 15점
    + 지역 일치(또는 전체) 25점
    + 용도 일치 30점
    + 예산 이내 20점 (예산+10만원 이내면 8점)
    + 최소 면적 충족 10점
    + 주차 필요&가능 8점 / 주차 불필요면 5점
    → 최대 98점으로 clamp, 점수 내림차순 정렬 후 상위 3건 표시
```
같은 가중치(15/25/30/20/10/8/5)로 `calculate_suitability()` [backend/recommendation.py]가 서버 쪽에도 존재하고, `routers/recommendations.py`가 이를 API로 노출합니다. 다만 현재 프론트(`submitRecommendation`)는 이 API를 호출하지 않고 **클라이언트에서 직접** 같은 로직을 다시 계산합니다 — 로직 두 벌이 중복돼 있는 상태입니다.

### 정식 데이터 반영 파이프라인 (CSV → PostgreSQL)

```
원본 CSV (project/data_pipeline/sample_raw.csv 또는 실제 수집 CSV)
  ↓ clean_spaces.py
    - normalize_text(): 공백·주소 문자열 정규화
    - parse_number(): "142.5㎡", "35만원" 같은 문자열 → 숫자 변환
    - clean_row(): 용도/상태 문자열 → 공통 코드 매핑(CATEGORY_CODES/STATUS_CODES), 행 단위 유효성 검사
    - clean_file(): 이름+주소 기준 중복 제거, 필수값 누락 행은 rejected로 분리
  ↓ (정제 결과를 spaces_import_template.csv 컬럼 형식으로 매핑: id, deposit, lat, lng, images 등 추가 입력)
  ↓ import_spaces.py
    - parse_row(): CSV 행 → SpaceCreate(Pydantic) 스키마로 변환
    - load_and_validate(): 재검증, id 중복 등 오류를 라인 번호와 함께 리포트
    - upsert(): --commit 플래그가 있을 때만 SQLAlchemy로 PostgreSQL의 Space/SpaceImage 테이블에 반영, DataSyncLog에 실행 이력 기록
  ↓
PostgreSQL (spaces 테이블 등)
  ↓  database.py: seed_spaces() 또는 routers/spaces.py의 API 조회
FastAPI 라우터 → 프론트(app.js)의 fetchJSON('/api/v1/spaces')가 받아서 렌더링
```

앱을 처음 띄울 때는 이 파이프라인을 거치지 않고 `database.py`의 `seed_spaces()`가 `seed_spaces.json`을 바로 적재합니다(`SEED_SPACES_ON_STARTUP=true`, 기본값). 실 데이터 파이프라인은 이 seed 데이터를 대체/보강하기 위한 별도 경로입니다.
