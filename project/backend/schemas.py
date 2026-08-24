"""API 요청·응답 스키마."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from backend.models import ApplicationStatus, ApplicationType, SpaceStatus, UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, min_length=9, max_length=30)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("이름은 공백을 제외하고 2자 이상이어야 합니다.")
        return stripped


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, min_length=9, max_length=30)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("이름은 공백을 제외하고 2자 이상이어야 합니다.")
        return stripped


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def require_different_password(self):
        if self.current_password == self.new_password:
            raise ValueError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        return self


class AccountDeactivate(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class UserPreferenceUpdate(BaseModel):
    preferred_district: str | None = Field(default=None, max_length=50)
    preferred_category: str | None = Field(default=None, max_length=50)
    max_monthly_rent: int | None = Field(default=None, ge=0)
    min_area: float | None = Field(default=None, ge=0)
    parking_required: bool = False
    project_summary: str | None = Field(default=None, max_length=1000)


class UserPreferenceResponse(UserPreferenceUpdate):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    updated_at: datetime
    is_complete: bool


class SpaceImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    alt_text: str | None
    sort_order: int


class SpaceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str
    district: str
    category: str
    category_name: str
    area: float
    deposit: int
    monthly_rent: int
    maintenance_fee: int
    parking: bool
    parking_spaces: int
    lat: float
    lng: float
    main_image_url: str | None
    description: str | None
    floor: str | None
    building_structure: str | None
    remodeling_status: str | None
    remodeling_support: str | None
    managing_agency: str | None
    agency_contact: str | None
    transport_info: str | None
    utilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    available_from: date | None
    source_name: str | None
    source_url: str | None
    source_updated_at: datetime | None
    status: SpaceStatus
    images: list[SpaceImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SpaceListResponse(BaseModel):
    total: int
    items: list[SpaceSummary]
    source: str = "database"


class FavoriteResponse(BaseModel):
    created_at: datetime
    space: SpaceSummary


class ApplicationCreate(BaseModel):
    space_id: str
    visit_date: date
    application_type: ApplicationType = ApplicationType.VISIT
    applicant_name: str = Field(min_length=2, max_length=100)
    applicant_phone: str = Field(min_length=9, max_length=30)
    message: str = Field(min_length=5, max_length=2000)


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_date: date
    application_type: ApplicationType
    applicant_name: str | None
    applicant_phone: str | None
    message: str
    status: ApplicationStatus
    review_note: str | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    space: SpaceSummary


class ApplicationReview(BaseModel):
    status: Literal[ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]
    review_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_rejection_reason(self):
        if self.status == ApplicationStatus.REJECTED and not (self.review_note or "").strip():
            raise ValueError("거절 처리 시 사유를 입력해야 합니다.")
        if self.review_note is not None:
            self.review_note = self.review_note.strip() or None
        return self


class AdminApplicationResponse(ApplicationResponse):
    user_id: int
    user_email: EmailStr
    user_name: str
    reviewed_by: int | None
    reviewed_at: datetime | None


class SpaceImageInput(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)


class SpaceCreate(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{2,30}$")
    name: str = Field(min_length=2, max_length=200)
    address: str = Field(min_length=5, max_length=300)
    district: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=50)
    category_name: str = Field(min_length=1, max_length=100)
    area: float = Field(gt=0)
    deposit: int = Field(default=0, ge=0)
    monthly_rent: int = Field(ge=0)
    maintenance_fee: int = Field(default=0, ge=0)
    parking: bool = False
    parking_spaces: int = Field(default=0, ge=0)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    main_image_url: str | None = Field(default=None, max_length=2000)
    description: str | None = None
    floor: str | None = Field(default=None, max_length=100)
    building_structure: str | None = Field(default=None, max_length=150)
    remodeling_status: str | None = Field(default=None, max_length=30)
    remodeling_support: str | None = None
    managing_agency: str | None = Field(default=None, max_length=200)
    agency_contact: str | None = Field(default=None, max_length=50)
    transport_info: str | None = None
    utilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    available_from: date | None = None
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    source_updated_at: datetime | None = None
    status: SpaceStatus = SpaceStatus.AVAILABLE
    images: list[SpaceImageInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_parking_spaces(self):
        if not self.parking:
            self.parking_spaces = 0
        return self


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = Field(default=None, min_length=5, max_length=300)
    district: str | None = Field(default=None, min_length=1, max_length=50)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    category_name: str | None = Field(default=None, min_length=1, max_length=100)
    area: float | None = Field(default=None, gt=0)
    deposit: int | None = Field(default=None, ge=0)
    monthly_rent: int | None = Field(default=None, ge=0)
    maintenance_fee: int | None = Field(default=None, ge=0)
    parking: bool | None = None
    parking_spaces: int | None = Field(default=None, ge=0)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    main_image_url: str | None = Field(default=None, max_length=2000)
    description: str | None = None
    floor: str | None = Field(default=None, max_length=100)
    building_structure: str | None = Field(default=None, max_length=150)
    remodeling_status: str | None = Field(default=None, max_length=30)
    remodeling_support: str | None = None
    managing_agency: str | None = Field(default=None, max_length=200)
    agency_contact: str | None = Field(default=None, max_length=50)
    transport_info: str | None = None
    utilities: list[str] | None = None
    tags: list[str] | None = None
    features: list[str] | None = None
    available_from: date | None = None
    source_name: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    source_updated_at: datetime | None = None
    status: SpaceStatus | None = None
    images: list[SpaceImageInput] | None = None


class RecommendationCriteria(BaseModel):
    preferred_district: str = Field(default="ALL", max_length=50)
    purpose_category: str = Field(min_length=1, max_length=50)
    max_monthly_rent: int = Field(ge=0)
    min_area: float = Field(ge=0)
    parking_required: bool = False


class RecommendationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    raw_score: int
    normalized_score: int
    reasons: list[str]
    space: SpaceSummary


class RecommendationResponse(BaseModel):
    run_id: int
    weight_version: str
    results: list[RecommendationResultResponse]


class RecommendationHistoryResponse(BaseModel):
    id: int
    preferred_district: str
    purpose_category: str
    max_monthly_rent: int
    min_area: float
    parking_required: bool
    weight_version: str
    created_at: datetime
    results: list[RecommendationResultResponse]


class SuitabilityResponse(BaseModel):
    space_id: str
    profile_complete: bool
    normalized_score: int | None = None
    raw_score: int | None = None
    weight_version: str | None = None
    reasons: list[str] = Field(default_factory=list)
