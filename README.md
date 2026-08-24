# 다시, 공간 (DASI SPACE)

> 대구 지역의 유휴 공간을 발견하고, 사용자 조건에 맞는 공간 추천부터 관심 등록과 방문·이용 신청까지 연결하는 공간 매칭 플랫폼

## 1. 프로젝트 소개

대구에는 활용 가능성이 있지만 정보가 여러 기관과 문서에 흩어져 있거나, 일반 사용자가 임대 조건과 이용 가능 여부를 한눈에 비교하기 어려운 유휴 공간이 존재합니다. **다시, 공간**은 이러한 공간 정보를 하나의 서비스에 모으고, 창업자·소상공인·예술가·커뮤니티 운영자 등이 자신의 조건에 맞는 공간을 쉽게 찾도록 돕는 프로젝트입니다.

사용자는 지역, 활용 업종, 월 예산, 최소 면적, 주차 필요 여부를 입력할 수 있습니다. 서비스는 각 공간과 조건을 비교해 적합도를 백분율로 보여주고 상위 공간을 추천합니다. 마음에 드는 공간은 관심 목록에 저장하거나 방문·이용을 신청할 수 있으며, 관리자는 공간 정보와 신청 상태를 관리합니다.

### 프로젝트 목적

- 흩어진 유휴 공간 정보를 검색 가능한 형태로 통합합니다.
- 가격·면적·위치·용도 등 핵심 조건의 비교 비용을 줄입니다.
- 사용자의 명시적인 선호 조건을 근거로 설명 가능한 추천을 제공합니다.
- 공간 탐색에서 관심 등록, 방문·이용 신청까지 하나의 흐름으로 연결합니다.
- 관리자가 공간과 사용자 신청을 실제 데이터베이스 기준으로 운영할 수 있게 합니다.

### 추천 방식

이 프로젝트는 텍스트 임베딩이나 생성형 AI를 사용하지 않습니다. 사용자가 직접 입력한 조건과 공간의 구조화된 데이터를 비교하는 **규칙·가중치 기반 추천 방식**을 사용합니다.

이 방식은 점수 산정 근거가 명확하고, 데이터가 많지 않은 초기 서비스에서도 안정적으로 동작하며, 운영자가 가중치를 조정하기 쉽다는 장점이 있습니다.

---

## 2. 주요 기능

### 사용자 기능

- 공간 목록 검색 및 지역·업종·가격·면적·주차 필터
- 공간 상세 정보, 사진, 위치 및 이용 조건 확인
- 회원가입·로그인과 JWT 기반 인증
- 마이페이지에서 개인 정보 및 추천 조건 관리
- 공간별 적합도 백분율과 추천 사유 확인
- 조건에 맞는 공간 TOP 3 추천
- 관심 공간 등록·해제
- 방문 또는 이용 신청 및 신청 취소
- 추천 결과와 신청 내역 조회
- 비밀번호 변경 및 계정 비활성화

### 관리자 기능

- 일반 사용자와 관리자의 역할 구분
- 공간 등록·수정·삭제
- 신청 목록 조회
- 신청 승인·거절과 검토 의견 기록
- 기준 공간 데이터 재동기화

### 데이터 관리 기능

- CSV 원본 데이터 정제 및 필수값 검증
- 공간 ID 기준 신규 등록·기존 데이터 갱신(upsert)
- 이미지, 편의시설, 특징, 태그 데이터 처리
- 동기화 결과와 오류 건수 기록

---

## 3. 현재 구현 현황

| 구분 | 상태 | 설명 |
|---|---|---|
| 프론트엔드 시연 화면 | 구현 | 공간 목록·필터·상세·지도·추천 화면 제공 |
| FastAPI 백엔드 | 구현 | 인증, 공간, 관심, 신청, 추천, 관리자 API 제공 |
| PostgreSQL 연동 | 구현 | SQLAlchemy ORM과 Alembic 마이그레이션 구성 |
| 규칙 기반 추천 | 구현 | 조건별 가중치 및 0~100% 정규화 |
| 공간 CSV 적재 | 구현 | 검증용 dry-run과 DB upsert 지원 |
| 프론트–백엔드 완전 통합 | 진행 필요 | 현재 저장소 루트 프론트는 `data.js` 기반 시연본 |
| 실제 공간 원본 데이터 | 데이터 필요 | 현재는 시연용 seed 데이터 사용 |
| Kakao 지도·로드뷰 | 키 필요 | 앱 키와 허용 도메인 등록 후 연결 가능 |
| 운영 배포 | 진행 필요 | 운영 서버, 도메인, HTTPS와 운영 시크릿 필요 |

> 현재 저장소에는 루트의 정적 프론트 시연본과 `project/backend`의 DB 기반 API가 함께 있습니다. 두 영역은 각각 실행할 수 있으며, 최종 통합 단계에서는 프론트 공간 데이터 요청을 REST API로 통일하고 FastAPI가 화면과 API를 같은 포트에서 제공하도록 정리합니다.

---

## 4. 추천 점수 계산

추천 엔진은 다음 항목을 공간 데이터와 비교합니다.

| 평가 항목 | 최대 점수 | 판정 기준 |
|---|---:|---|
| 기본 점수 | 15 | 모든 후보 공간에 적용 |
| 지역 | 25 | 선호 지역과 일치하거나 대구 전역 선택 |
| 활용 업종 | 30 | 희망 업종과 공간 분류 일치 |
| 월 예산 | 20 | 월 임대료가 예산 이내 |
| 예산 근접 | 8 | 예산보다 높지만 10만 원 이내인 경우 |
| 최소 면적 | 10 | 공간 면적이 요구 면적 이상 |
| 주차 | 8 | 주차가 필요하고 해당 공간에 주차 가능 |
| 주차 선택 안 함 | 5 | 주차가 필수 조건이 아닐 때 적용 |

후보 공간의 원점수를 해당 조건에서 받을 수 있는 최대 점수로 나눠 백분율로 정규화합니다.

```text
사용자 추천 조건
  → 지역·업종·예산·면적·주차 조건 비교
  → 조건별 가중치 합산
  → 0~100% 적합도로 정규화
  → 점수순 정렬
  → 상위 3개 공간과 추천 사유 반환
```

추천 가중치는 `recommendation_weight_configs` 테이블에서 버전별로 관리하므로, 코드 전체를 수정하지 않고도 운영 정책에 맞춰 조정할 수 있습니다.

---

## 5. 아키텍처와 처리 흐름

### 백엔드 처리 구조

```text
Client
  → FastAPI Router
    → 인증·권한 및 요청 데이터 검증
      → 추천/신청/공간 도메인 로직
        → SQLAlchemy ORM
          → PostgreSQL
```

### 전체 서비스 목표 구조

```text
브라우저 (HTML + CSS + JavaScript)
  ├─ 회원가입·로그인·마이페이지
  ├─ 공간 검색·필터·상세
  ├─ 관심 공간·방문/이용 신청
  ├─ 추천 조건·적합도·TOP 3
  └─ 지도·로드뷰
            │
            ▼
FastAPI (/api/v1)
  ├─ Auth / Users
  ├─ Spaces / Favorites
  ├─ Applications
  ├─ Recommendations
  └─ Admin
            │
            ▼
SQLAlchemy → PostgreSQL
```

### 공간 데이터 적재 흐름

```text
공간 원본 CSV
  → 필수값·자료형·공통 코드 검증
  → dry-run 결과 확인
  → 공간 ID 기준 upsert
  → PostgreSQL 저장
  → 공간 목록·상세 API
  → 사용자 화면
```

---

## 6. 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Map | Leaflet, OpenStreetMap |
| 예정 지도 연동 | Kakao Maps JavaScript API, Kakao Roadview |
| Backend | Python, FastAPI, Uvicorn |
| Validation | Pydantic, Pydantic Settings |
| Database | PostgreSQL |
| ORM / Migration | SQLAlchemy 2, Alembic |
| Authentication | JWT(PyJWT), Argon2(pwdlib) |
| Test | Pytest, FastAPI TestClient, HTTPX |
| Data Pipeline | Python CSV/JSON 처리, Pydantic 검증 |

프론트엔드는 별도의 Node.js 빌드 과정이 없는 정적 웹 구조이며, 백엔드는 REST API와 데이터베이스 처리를 담당합니다.

---

## 7. 프로젝트 구조

```text
DIP_PYTHON_PROJECT/
├─ index.html                  # 프론트엔드 화면
├─ styles.css                 # 전체 스타일 및 반응형 UI
├─ app.js                     # 검색·상세·추천·지도 UI 로직
├─ data.js                    # 현재 프론트 시연용 공간 데이터
├─ README.md
└─ project/
   ├─ .gitignore
   ├─ backend/
   │  ├─ main.py              # FastAPI 앱 조립 및 진입점
   │  ├─ config.py            # 환경 변수 설정
   │  ├─ database.py          # DB 세션·초기화·seed 적재
   │  ├─ models.py            # SQLAlchemy ORM 모델
   │  ├─ schemas.py           # API 요청·응답 스키마
   │  ├─ security.py          # 비밀번호 해시·JWT 처리
   │  ├─ dependencies.py      # 인증 사용자·관리자·DB 의존성
   │  ├─ recommendation.py    # 규칙·가중치 기반 추천 엔진
   │  ├─ seed_spaces.json     # 시연용 공간 기준 데이터
   │  ├─ requirements.txt
   │  ├─ routers/
   │  │  ├─ auth.py
   │  │  ├─ users.py
   │  │  ├─ spaces.py
   │  │  ├─ favorites.py
   │  │  ├─ applications.py
   │  │  ├─ recommendations.py
   │  │  └─ admin.py
   │  ├─ migrations/          # Alembic 마이그레이션 이력
   │  └─ tests/               # API 통합 테스트
   └─ data_pipeline/
      ├─ sample_raw.csv
      ├─ spaces_import_template.csv
      ├─ clean_spaces.py      # 원본 데이터 1차 정제
      └─ import_spaces.py     # 검증 및 PostgreSQL upsert
```

---

## 8. 로컬 실행 방법

### 사전 준비

- Python 3.11 이상
- PostgreSQL 또는 Docker
- Git

기본 DB 연결 정보는 다음과 같습니다.

```text
Host: localhost
Port: 5433
Database: dasi_space
User: dasi_space
Password: dasi_space
```

### 8.1 PostgreSQL 실행

로컬 PostgreSQL을 직접 구성하거나, Docker가 설치되어 있다면 개발용 DB 컨테이너를 생성할 수 있습니다.

```powershell
docker run --name dasi-space-db `
  -e POSTGRES_DB=dasi_space `
  -e POSTGRES_USER=dasi_space `
  -e POSTGRES_PASSWORD=dasi_space `
  -p 5433:5432 `
  -d postgres:17-alpine
```

이미 컨테이너를 생성했다면 이후에는 다음 명령으로 실행합니다.

```powershell
docker start dasi-space-db
```

### 8.2 백엔드 설치

```powershell
cd project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

### 8.3 환경 변수 설정

`project/.env` 파일을 생성합니다.

```dotenv
APP_NAME=다시, 공간 API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://dasi_space:dasi_space@localhost:5433/dasi_space

JWT_SECRET=development-only-change-this-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

CORS_ORIGINS=http://localhost:8001,http://127.0.0.1:8001,http://localhost:5500
ALLOWED_HOSTS=*
AUTO_CREATE_TABLES=true
SEED_SPACES_ON_STARTUP=true

BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=admin-password-1234
BOOTSTRAP_ADMIN_NAME=운영 관리자

# 발급 후 입력
KAKAO_MAP_APP_KEY=
```

> 개발용 기본 시크릿과 관리자 비밀번호를 운영 환경에서 그대로 사용하면 안 됩니다.

### 8.4 백엔드 API 실행

`project` 폴더에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8001
```

- API 문서: `http://127.0.0.1:8001/docs`
- 대체 API 문서: `http://127.0.0.1:8001/redoc`
- 상태 확인: `http://127.0.0.1:8001/health`
- 공간 목록 API: `http://127.0.0.1:8001/api/v1/spaces`

`AUTO_CREATE_TABLES=true`이면 개발 환경에서 테이블이 자동 생성되고, `SEED_SPACES_ON_STARTUP=true`이면 시연용 공간 데이터가 동기화됩니다.

### 8.5 현재 프론트 시연본 실행

새 터미널에서 저장소 루트로 이동한 뒤 정적 서버를 실행합니다.

```powershell
python -m http.server 5500
```

브라우저에서 `http://127.0.0.1:5500`에 접속합니다.

현재 루트 프론트 시연본의 공간 목록은 `data.js`를 사용합니다. DB 기반 통합본에서는 이 부분을 `/api/v1/spaces` 요청으로 교체하고 FastAPI와 같은 출처에서 제공해야 합니다.

---

## 9. 주요 API

모든 API 기본 경로는 `/api/v1`입니다.

### 인증·사용자

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/auth/signup` | 회원가입 |
| `POST` | `/auth/login` | 로그인 및 JWT 발급 |
| `GET` | `/users/me` | 내 정보 조회 |
| `PATCH` | `/users/me` | 내 정보 수정 |
| `PATCH` | `/users/me/password` | 비밀번호 변경 |
| `POST` | `/users/me/deactivate` | 계정 비활성화 |
| `GET` | `/users/me/preferences` | 추천 조건 조회 |
| `PUT` | `/users/me/preferences` | 추천 조건 저장 |

### 공간·추천

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/spaces` | 공간 목록·검색·필터·페이지 조회 |
| `GET` | `/spaces/{space_id}` | 공간 상세 조회 |
| `GET` | `/spaces/{space_id}/suitability` | 현재 사용자의 공간 적합도 조회 |
| `POST` | `/recommendations` | 추천 TOP 3 생성 및 저장 |
| `GET` | `/recommendations/me` | 내 추천 이력 조회 |

### 관심 공간·신청

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/favorites` | 내 관심 공간 조회 |
| `POST` | `/favorites/{space_id}` | 관심 공간 등록 |
| `DELETE` | `/favorites/{space_id}` | 관심 공간 해제 |
| `GET` | `/applications/me` | 내 신청 내역 조회 |
| `POST` | `/applications` | 방문·이용 신청 |
| `PATCH` | `/applications/{application_id}/cancel` | 신청 취소 |

### 관리자

| Method | Endpoint | 설명 |
|---|---|---|
| `GET` | `/admin/users` | 사용자 목록 조회 |
| `GET` | `/admin/applications` | 신청 목록·상태별 조회 |
| `PATCH` | `/admin/applications/{id}/review` | 신청 승인·거절 |
| `POST` | `/admin/spaces` | 공간 등록 |
| `PATCH` | `/admin/spaces/{space_id}` | 공간 수정 |
| `DELETE` | `/admin/spaces/{space_id}` | 공간 삭제 |
| `POST` | `/admin/data-sync/seed` | 기준 데이터 동기화 |

인증이 필요한 API에는 다음 헤더를 전송합니다.

```http
Authorization: Bearer <access_token>
```

---

## 10. 데이터베이스 구성

| 테이블 | 역할 |
|---|---|
| `users` | 사용자 계정, 역할, 활성 상태 |
| `user_preferences` | 지역·업종·예산·면적·주차 추천 조건 |
| `spaces` | 공간 기본 정보, 가격, 면적, 위치, 운영 정보 |
| `space_images` | 공간별 다중 이미지 |
| `favorites` | 사용자와 관심 공간의 연결 |
| `applications` | 방문·이용 신청 및 관리자 검토 상태 |
| `recommendation_weight_configs` | 버전별 추천 가중치 |
| `recommendation_runs` | 사용자가 실행한 추천 조건과 시점 |
| `recommendation_results` | 추천 순위, 점수, 추천 사유 |
| `data_sync_logs` | 공간 데이터 적재 결과와 오류 기록 |

---

## 11. 실제 공간 데이터 적재

`project/data_pipeline/spaces_import_template.csv` 형식으로 데이터를 준비합니다.

먼저 DB를 변경하지 않는 dry-run으로 검증합니다.

```powershell
cd project
.\.venv\Scripts\python.exe data_pipeline\import_spaces.py data_pipeline\spaces_import_template.csv
```

검증 오류가 없으면 `--commit` 옵션으로 반영합니다.

```powershell
.\.venv\Scripts\python.exe data_pipeline\import_spaces.py data_pipeline\spaces_import_template.csv --commit
```

기존 공간 ID는 갱신하고 새로운 ID는 추가합니다. 입력 파일에 없는 기존 공간을 자동으로 삭제하지는 않습니다.

---

## 12. Kakao 지도와 로드뷰 연결 계획

공간 데이터에는 `lat`, `lng` 좌표가 있으므로 상세 화면에서 사진·지도·로드뷰 탭을 제공할 수 있습니다.

```text
공간 상세 조회
  → 공간의 lat·lng 확인
  → Kakao RoadviewClient로 인근 파노라마 조회
  → 결과가 있으면 로드뷰 표시
  → 결과가 없으면 지도와 안내 문구 표시
```

Kakao Developers에서 JavaScript 앱 키를 발급하고 로컬 및 운영 도메인을 허용 목록에 등록한 뒤 `project/.env`에 설정합니다.

```dotenv
KAKAO_MAP_APP_KEY=발급받은_JavaScript_앱_키
```

로드뷰는 모든 좌표에 존재하지 않으므로, 인근 파노라마가 없는 공간에 대한 대체 UI가 필요합니다.

---

## 13. 테스트

PostgreSQL이 실행 중이고 테스트용 관리자 설정이 준비된 상태에서 다음 명령을 실행합니다.

```powershell
cd project
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

테스트 범위에는 다음 항목이 포함됩니다.

- 정적 파일 외 프로젝트 내부 파일 비공개 확인
- DB seed와 공간 필터
- 회원가입·로그인·JWT 인증·권한
- 비밀번호 변경·계정 비활성화
- 사용자 추천 조건과 공간 적합도
- 관심 공간·신청·취소
- 관리자 신청 승인 흐름
- 관리자 공간 CRUD

---

## 14. 보안 및 운영 시 확인 사항

- 운영 환경에서는 충분히 긴 무작위 `JWT_SECRET`을 사용합니다.
- 관리자 초기 비밀번호와 DB 비밀번호를 반드시 변경합니다.
- `.env` 파일을 Git에 커밋하지 않습니다.
- 운영 도메인만 `CORS_ORIGINS`와 `ALLOWED_HOSTS`에 등록합니다.
- 운영 DB 변경은 `AUTO_CREATE_TABLES` 대신 Alembic 마이그레이션으로 관리합니다.
- HTTPS를 적용하고 토큰 저장 및 로그의 개인정보 노출 여부를 점검합니다.
- 공간 이미지와 외부 데이터는 사용 권한과 출처를 확인합니다.

백엔드는 운영 환경에서 개발용 JWT 시크릿을 감지하면 시작을 중단하도록 구성되어 있습니다.

---

## 15. 다음 작업

1. 루트 프론트의 `data.js` 의존성을 공간 REST API로 교체
2. 프론트 파일과 FastAPI 정적 파일 경로를 하나의 실행 구조로 통합
3. 실제 공간 원본 데이터 확보 및 DB 적재
4. Kakao Maps JavaScript 키 적용
5. 공간 상세 화면에 지도·로드뷰 탭과 미지원 안내 추가
6. 브라우저 E2E 테스트 및 모바일 화면 점검
7. 운영 서버·도메인·HTTPS 구성 후 배포

---

## 16. 프로젝트 핵심 가치

**다시, 공간**은 AI 기술 자체를 보여주기 위한 프로젝트가 아니라, 실제 사용자가 자신의 조건에 맞는 유휴 공간을 이해하기 쉽고 설명 가능한 방식으로 찾도록 돕는 서비스입니다. 구조화된 공간 데이터, 명확한 추천 기준, 신청과 관리까지 이어지는 서비스 흐름을 통해 사용되지 않는 공간이 다시 활용될 가능성을 높이는 것이 최종 목표입니다.
