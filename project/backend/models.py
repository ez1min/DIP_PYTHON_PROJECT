"""SQLAlchemy ORM 모델.

관심 공간과 방문 신청 API는 다음 단계에서 연결하지만, 데이터 구조가 다시
변하지 않도록 1차 DB 스키마에 함께 정의한다.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class SpaceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    REMODELING = "REMODELING"


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApplicationType(str, Enum):
    VISIT = "VISIT"
    USE = "USE"


class SyncStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, native_enum=False, length=20), default=UserRole.USER, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    favorites: Mapped[list[Favorite]] = relationship(back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list[Application]] = relationship(
        back_populates="applicant", foreign_keys="Application.user_id", cascade="all, delete-orphan"
    )
    preference: Mapped[UserPreference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    recommendation_runs: Mapped[list[RecommendationRun]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Space(TimestampMixin, Base):
    __tablename__ = "spaces"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str] = mapped_column(String(300), default="")
    district: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    category_name: Mapped[str] = mapped_column(String(100), default="")
    area: Mapped[float] = mapped_column(Float)
    deposit: Mapped[int] = mapped_column(Integer, default=0)
    monthly_rent: Mapped[int] = mapped_column(Integer)
    maintenance_fee: Mapped[int] = mapped_column(Integer, default=0)
    parking: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    parking_spaces: Mapped[int] = mapped_column(Integer, default=0)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    main_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    floor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    building_structure: Mapped[str | None] = mapped_column(String(150), nullable=True)
    remodeling_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    remodeling_support: Mapped[str | None] = mapped_column(Text, nullable=True)
    managing_agency: Mapped[str | None] = mapped_column(String(200), nullable=True)
    agency_contact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transport_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    utilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SpaceStatus] = mapped_column(
        SqlEnum(SpaceStatus, native_enum=False, length=20), default=SpaceStatus.AVAILABLE, index=True
    )

    images: Mapped[list[SpaceImage]] = relationship(
        back_populates="space", cascade="all, delete-orphan", order_by="SpaceImage.sort_order"
    )
    favorites: Mapped[list[Favorite]] = relationship(back_populates="space", cascade="all, delete-orphan")
    applications: Mapped[list[Application]] = relationship(back_populates="space")
    recommendation_results: Mapped[list[RecommendationResult]] = relationship(back_populates="space")


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_district: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_monthly_rent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    parking_required: Mapped[bool] = mapped_column(Boolean, default=False)
    project_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="preference")

    @property
    def is_complete(self) -> bool:
        return bool(
            self.preferred_category
            and self.max_monthly_rent is not None
            and self.min_area is not None
        )


class RecommendationWeightConfig(Base):
    __tablename__ = "recommendation_weight_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(30), unique=True)
    purpose_category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    base_score: Mapped[int] = mapped_column(Integer, default=15)
    district_weight: Mapped[int] = mapped_column(Integer, default=25)
    category_weight: Mapped[int] = mapped_column(Integer, default=30)
    budget_weight: Mapped[int] = mapped_column(Integer, default=20)
    near_budget_weight: Mapped[int] = mapped_column(Integer, default=8)
    area_weight: Mapped[int] = mapped_column(Integer, default=10)
    parking_weight: Mapped[int] = mapped_column(Integer, default=8)
    parking_optional_weight: Mapped[int] = mapped_column(Integer, default=5)
    score_cap: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list[RecommendationRun]] = relationship(back_populates="weight_config")


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    preferred_district: Mapped[str] = mapped_column(String(50), default="ALL")
    purpose_category: Mapped[str] = mapped_column(String(50))
    max_monthly_rent: Mapped[int] = mapped_column(Integer)
    min_area: Mapped[float] = mapped_column(Float)
    parking_required: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_config_id: Mapped[int] = mapped_column(ForeignKey("recommendation_weight_configs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="recommendation_runs")
    weight_config: Mapped[RecommendationWeightConfig] = relationship(back_populates="runs")
    results: Mapped[list[RecommendationResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RecommendationResult.rank"
    )


class RecommendationResult(Base):
    __tablename__ = "recommendation_results"
    __table_args__ = (UniqueConstraint("run_id", "rank", name="uq_recommendation_run_rank"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_runs.id", ondelete="CASCADE"), index=True
    )
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    raw_score: Mapped[int] = mapped_column(Integer)
    normalized_score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RecommendationRun] = relationship(back_populates="results")
    space: Mapped[Space] = relationship(back_populates="recommendation_results")


class SpaceImage(Base):
    __tablename__ = "space_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    space: Mapped[Space] = relationship(back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="favorites")
    space: Mapped[Space] = relationship(back_populates="favorites")


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id", ondelete="RESTRICT"), index=True)
    visit_date: Mapped[date] = mapped_column(Date)
    application_type: Mapped[ApplicationType] = mapped_column(
        SqlEnum(ApplicationType, native_enum=False, length=20), default=ApplicationType.VISIT
    )
    applicant_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applicant_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        SqlEnum(ApplicationStatus, native_enum=False, length=20),
        default=ApplicationStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    applicant: Mapped[User] = relationship(back_populates="applications", foreign_keys=[user_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])
    space: Mapped[Space] = relationship(back_populates="applications")


class DataSyncLog(Base):
    __tablename__ = "data_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100))
    status: Mapped[SyncStatus] = mapped_column(SqlEnum(SyncStatus, native_enum=False, length=20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
