"""DB 엔진, 요청별 세션, 초기 스키마와 seed 적재."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import get_settings
from backend.models import Base, RecommendationWeightConfig, Space, SpaceImage, User, UserRole
from backend.security import hash_password


BASE_DIR = Path(__file__).resolve().parent
SEED_PATH = BASE_DIR / "seed_spaces.json"
settings = get_settings()

engine_options: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        engine_options["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    """개발 환경의 첫 실행을 지원한다.

    운영 배포에서는 AUTO_CREATE_TABLES=false로 두고 Alembic migration을 사용한다.
    """
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if settings.seed_spaces_on_startup:
            seed_spaces(db)
            seed_recommendation_weights(db)
        bootstrap_admin(db)


def seed_spaces(db: Session) -> int:
    raw_spaces = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    existing = {
        space.id: space
        for space in db.scalars(
            select(Space)
            .where(Space.id.in_([item["id"] for item in raw_spaces]))
            .options(selectinload(Space.images))
        )
    }
    created = 0
    for item in raw_spaces:
        values = {key: value for key, value in item.items() if key != "images"}
        space = existing.get(item["id"])
        if space is None:
            space = Space(**values)
            db.add(space)
            created += 1
        else:
            # seed는 개발·시연 데이터의 단일 원본이므로 같은 ID의 모든 표시 필드를 맞춘다.
            for field, value in values.items():
                if field != "id":
                    setattr(space, field, value)

        space.images.clear()
        for image in item.get("images", []):
            space.images.append(SpaceImage(**image))
    db.commit()
    return created


def seed_recommendation_weights(db: Session) -> RecommendationWeightConfig:
    config = db.scalar(
        select(RecommendationWeightConfig).where(RecommendationWeightConfig.version == "ppt-v0.1")
    )
    if config is not None:
        return config

    config = RecommendationWeightConfig(
        version="ppt-v0.1",
        base_score=15,
        district_weight=25,
        category_weight=30,
        budget_weight=20,
        near_budget_weight=8,
        area_weight=10,
        parking_weight=8,
        parking_optional_weight=5,
        score_cap=100,
        is_active=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def bootstrap_admin(db: Session) -> User | None:
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password
    if not email or not password:
        return None
    if len(password) < 8:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD는 8자 이상이어야 합니다.")

    normalized_email = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        return existing

    admin = User(
        email=normalized_email,
        password_hash=hash_password(password),
        name=settings.bootstrap_admin_name,
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def database_is_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
