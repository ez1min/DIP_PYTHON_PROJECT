"""환경 변수 기반 애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "다시, 공간 API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://dasi_space:dasi_space@localhost:5433/dasi_space"

    jwt_secret: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:8001,http://127.0.0.1:8001"
    allowed_hosts: str = "*"
    auto_create_tables: bool = True
    seed_spaces_on_startup: bool = True
    kakao_map_app_key: str | None = None

    # 값이 모두 설정된 경우에만 최초 관리자 계정을 생성한다.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_name: str = "운영 관리자"

    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_names(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def uses_development_secret(self) -> bool:
        return self.jwt_secret == "development-only-change-this-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()
