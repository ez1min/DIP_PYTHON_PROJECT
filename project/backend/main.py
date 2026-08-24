"""다시, 공간 FastAPI 애플리케이션 진입점."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse

from backend.config import PROJECT_DIR, get_settings
from backend.database import database_is_ready, initialize_database
from backend.routers import admin, applications, auth, favorites, recommendations, spaces, users


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env.lower() == "production" and settings.uses_development_secret:
        raise RuntimeError("운영 환경에서는 JWT_SECRET을 반드시 변경해야 합니다.")
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="프론트엔드, PostgreSQL, JWT 인증을 한 서버에서 제공하는 다시, 공간 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_names)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(users.admin_router, prefix=settings.api_prefix)
app.include_router(spaces.router, prefix=settings.api_prefix)
app.include_router(favorites.router, prefix=settings.api_prefix)
app.include_router(applications.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/health", tags=["시스템"])
def health() -> dict:
    database_ready = database_is_ready()
    return {
        "status": "ok" if database_ready else "degraded",
        "database": "connected" if database_ready else "disconnected",
        "authentication": "jwt",
        "development_secret_in_use": settings.uses_development_secret,
        "implemented": [
            "frontend_serving",
            "postgresql",
            "space_list",
            "space_detail",
            "signup",
            "login",
            "me",
            "mypage_preferences",
            "favorites",
            "applications",
            "recommendations",
            "suitability_score",
            "admin_role",
            "admin_application_review",
            "admin_space_management",
            "database_catalog",
        ],
        "todo": ["public_data_source", "kakao_map_app_key", "production_deployment"],
    }


@app.get(f"{settings.api_prefix}/config/public", tags=["시스템"])
def public_config() -> dict:
    return {
        "map_provider": "kakao" if settings.kakao_map_app_key else "leaflet",
        "kakao_map_app_key": settings.kakao_map_app_key,
    }


# 프로젝트 루트를 StaticFiles로 공개하지 않고 브라우저에 필요한 파일만 제공한다.
@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(PROJECT_DIR / "index.html", media_type="text/html")


@app.get("/styles.css", include_in_schema=False)
def frontend_styles() -> FileResponse:
    return FileResponse(PROJECT_DIR / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def frontend_app() -> FileResponse:
    return FileResponse(PROJECT_DIR / "app.js", media_type="text/javascript")
