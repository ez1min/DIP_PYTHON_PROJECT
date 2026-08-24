"""'다시, 공간' 프론트엔드(FE/DIP_PYTHON_PROJECT/data.js)와 주고받는 데이터 계약.

필드 이름은 프론트가 그대로 읽으므로 camelCase를 유지한다.
파이썬 쪽에서는 snake_case로 쓰고 직렬화할 때 별칭으로 바꾼다.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from pydantic.alias_generators import to_camel


# --------------------------------------------------------------------------
# 공통 코드 (data.js의 COMMON_CODES)
# --------------------------------------------------------------------------


class Category(str, Enum):
    """공간 용도 분류."""

    STARTUP = "STARTUP"
    SHOP = "SHOP"
    OFFICE = "OFFICE"
    ART = "ART"
    WORKSHOP = "WORKSHOP"
    SOCIAL = "SOCIAL"

    @property
    def label(self) -> str:
        return _CATEGORY_LABELS[self]


_CATEGORY_LABELS: dict[Category, str] = {
    Category.STARTUP: "청년 창업",
    Category.SHOP: "소규모 상점",
    Category.OFFICE: "사무실",
    Category.ART: "문화·예술",
    Category.WORKSHOP: "작업실",
    Category.SOCIAL: "사회적기업",
}


class District(str, Enum):
    """대구광역시 9개 구·군. 2023년 편입된 군위군을 포함한다."""

    JUNG = "중구"
    DONG = "동구"
    SEO = "서구"
    NAM = "남구"
    BUK = "북구"
    SUSEONG = "수성구"
    DALSEO = "달서구"
    DALSEONG = "달성군"
    GUNWI = "군위군"


class SpaceStatus(str, Enum):
    """공간 이용 상태."""

    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_USE = "IN_USE"
    REMODELING = "REMODELING"
    UNAVAILABLE = "UNAVAILABLE"

    @property
    def label(self) -> str:
        return _STATUS_LABELS[self]


_STATUS_LABELS: dict[SpaceStatus, str] = {
    SpaceStatus.AVAILABLE: "이용 가능",
    SpaceStatus.RESERVED: "예약 중",
    SpaceStatus.IN_USE: "이용 중",
    SpaceStatus.REMODELING: "리모델링 중",
    SpaceStatus.UNAVAILABLE: "이용 불가",
}


class RemodelingStatus(str, Enum):
    """리모델링 진행 단계."""

    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIAL = "PARTIAL"
    SUPPORT_ELIGIBLE = "SUPPORT_ELIGIBLE"
    NONE = "NONE"


class UserType(str, Enum):
    GENERAL = "GENERAL"
    PROVIDER = "PROVIDER"
    ADMIN = "ADMIN"


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SyncStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DealType(str, Enum):
    """실거래 신고 유형. 현재 파이프라인은 매매(SALE)만 수집한다.

    국토부 실거래가 공개시스템에 상업업무용·공장창고용 전월세 신고 데이터셋은
    없다(주택 계열만 전월세를 공개한다). JEONSE/MONTHLY_RENT는 스키마상
    자리만 마련해둔 것이고, 실제로 채워지는 값은 아직 SALE뿐이다.
    """

    SALE = "SALE"
    JEONSE = "JEONSE"
    MONTHLY_RENT = "MONTHLY_RENT"


# --------------------------------------------------------------------------
# 공통 베이스
# --------------------------------------------------------------------------


class CamelModel(BaseModel):
    """프론트가 읽는 camelCase로 직렬화하는 공통 베이스."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )


# 대구 시역을 벗어난 좌표는 지오코딩 실패로 간주한다.
Latitude = Annotated[float, Field(ge=35.5, le=36.3)]
Longitude = Annotated[float, Field(ge=128.2, le=129.0)]

# 금액 단위는 만원. 프론트 formatMoney()가 그렇게 표시한다.
Manwon = Annotated[int, Field(ge=0)]


# --------------------------------------------------------------------------
# 실거래가
# --------------------------------------------------------------------------


class TransactionInfo(CamelModel):
    """국토부 실거래가 공개시스템에서 지번으로 매칭된 거래 1건."""

    deal_type: DealType
    deal_amount: Manwon = Field(description="매매가 또는 전세보증금(만원)")
    monthly_rent: Manwon | None = Field(default=None, description="월세일 때만 값이 있음")
    deal_date: date
    building_use: str = Field(default="", description="신고서상 건물 용도(예: 공장, 제2종근린생활)")
    source: str = Field(description="예: '국토부 실거래가(상업업무용)', '국토부 실거래가(공장·창고용)'")


# --------------------------------------------------------------------------
# Space
# --------------------------------------------------------------------------


class Space(CamelModel):
    """유휴공간 1건. data.js의 INITIAL_SPACES 원소와 1:1 대응한다."""

    id: str = Field(pattern=r"^SPC-[A-Z0-9]{3,}$", examples=["SPC-001", "SPC-P001"])
    name: str = Field(min_length=1, max_length=120)

    category: Category
    district: District
    address: str = Field(min_length=1)
    lat: Latitude
    lng: Longitude

    area: float = Field(gt=0, description="전용 면적(㎡)")
    deposit: Manwon = Field(description="보증금(만원)")
    monthly_rent: Manwon = Field(description="월 임대료(만원)")
    maintenance_fee: Manwon = Field(default=0, description="관리비(만원)")

    status: SpaceStatus = SpaceStatus.AVAILABLE
    remodeling_status: RemodelingStatus = RemodelingStatus.NONE
    remodeling_support: str = ""

    managing_agency: str = Field(min_length=1)
    agency_contact: str = Field(min_length=1)

    # 프론트가 photos[0]을 널 가드 없이 읽으므로 최소 1장을 강제한다.
    photos: list[str] = Field(min_length=1)

    floor: str = ""
    structure: str = ""
    parking: bool = False
    parking_spaces: int = Field(default=0, ge=0)

    # features/utilities도 프론트에서 널 가드 없이 .map()을 돈다.
    utilities: list[str] = Field(default_factory=list)
    transport_info: str = ""
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    features: list[str] = Field(default_factory=list)

    created_at: date
    views: int = Field(default=0, ge=0)
    favorite_count: int = Field(default=0, ge=0)

    # 국토부 실거래가(상업업무용/공장창고용)에서 지번으로 매칭된 최근 거래.
    # 매칭 실패(거래 없음 · 지번 마스킹으로 확인 불가)면 None.
    last_transaction: TransactionInfo | None = None

    @field_validator("photos")
    @classmethod
    def _photos_must_be_http(cls, value: list[str]) -> list[str]:
        for url in value:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"사진 URL이 http(s)로 시작하지 않음: {url}")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category_name(self) -> str:
        """프론트가 표시·검색에 쓰는 한글 분류명."""
        return self.category.label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_name(self) -> str:
        return self.status.label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pyeong(self) -> float:
        """면적을 평으로 환산. 1평 = 3.3058㎡."""
        return round(self.area / 3.3058, 1)

    @property
    def parking_available(self) -> bool:
        """주차 대수와 불리언 플래그가 어긋날 때 대수를 신뢰한다."""
        return self.parking or self.parking_spaces > 0


# --------------------------------------------------------------------------
# 사용자 액션
# --------------------------------------------------------------------------


class ApplicationCreate(CamelModel):
    """방문·이용 신청 접수 입력. 클라이언트가 실제로 보내는 필드만 받는다.

    id/status/createdAt은 클라이언트가 위조할 수 있는 값이라 여기 포함하지 않고
    서버가 채운다.
    """

    space_id: str = Field(pattern=r"^SPC-[A-Z0-9]{3,}$")
    name: str = Field(min_length=1, max_length=40)
    phone: str = Field(pattern=r"^0\d{1,2}-?\d{3,4}-?\d{4}$")
    visit_date: date
    message: str = ""


class Application(ApplicationCreate):
    """저장된 신청 1건. ApplicationCreate + 서버 생성 필드."""

    id: str = Field(examples=["APP-1755000000000"])
    status: ApplicationStatus = ApplicationStatus.PENDING
    created_at: datetime


class RecommendCriteria(CamelModel):
    """추천 입력값. 저장하지 않고 점수 계산에만 쓴다."""

    # 프론트 select의 sentinel 값 "ALL"을 그대로 받는다("대구 전역").
    district: District | Literal["ALL"] = Field(default="ALL")
    purpose: Category
    budget: Manwon = Field(description="월 예산(만원)")
    area: float = Field(ge=0, description="희망 최소 면적(㎡)")
    parking: bool = False


class RecommendResult(CamelModel):
    """추천 결과 1건. app.js가 상위 3건만 렌더링한다."""

    space: Space
    score: int = Field(ge=0, le=98)
    reasons: list[str] = Field(default_factory=list)


class SyncLog(CamelModel):
    """공공데이터 동기화 이력. 운영센터 화면에 쌓인다."""

    timestamp: datetime
    source: str
    status: SyncStatus
    count: int = Field(ge=0)
    note: str = ""


# --------------------------------------------------------------------------
# 프론트 부팅용 설정
# --------------------------------------------------------------------------


class ClientConfig(CamelModel):
    """프론트가 부팅 시 필요로 하는 클라이언트 키.

    Kakao JS 키는 도메인 제한이 걸리는 공개용 키라(구글 지도 JS 키와 동일한
    성격) 브라우저에 노출돼도 되지만, 그렇다고 정적 파일에 하드코딩해
    git에 박아두지는 않는다 — .env 하나만 바꾸면 되도록 서버가 내려준다.
    """

    kakao_js_key: str


class CodeItem(CamelModel):
    code: str
    name: str


class CategoryCode(CodeItem):
    icon: str
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class StatusCode(CodeItem):
    badge_class: str


class CommonCodes(CamelModel):
    """data.js의 COMMON_CODES를 그대로 내려주는 응답 모델."""

    user_types: list[CodeItem]
    categories: list[CategoryCode]
    districts: list[str]
    statuses: list[StatusCode]

    @classmethod
    def default(cls) -> "CommonCodes":
        icons = {
            Category.STARTUP: ("rocket", "#10B981"),
            Category.SHOP: ("shopping-bag", "#F59E0B"),
            Category.OFFICE: ("briefcase", "#3B82F6"),
            Category.ART: ("palette", "#8B5CF6"),
            Category.WORKSHOP: ("hammer", "#EC4899"),
            Category.SOCIAL: ("heart-handshake", "#14B8A6"),
        }
        badges = {
            SpaceStatus.AVAILABLE: "badge-success",
            SpaceStatus.RESERVED: "badge-warning",
            SpaceStatus.IN_USE: "badge-info",
            SpaceStatus.REMODELING: "badge-purple",
            SpaceStatus.UNAVAILABLE: "badge-danger",
        }
        user_type_names = {
            UserType.GENERAL: "일반 사용자 (청년/창업/예술)",
            UserType.PROVIDER: "공간 제공자 (건물주/기관)",
            UserType.ADMIN: "관리자 (대구광역시/운영사)",
        }
        return cls(
            user_types=[
                CodeItem(code=member.value, name=user_type_names[member])
                for member in UserType
            ],
            categories=[
                CategoryCode(
                    code=member.value,
                    name=member.label,
                    icon=icons[member][0],
                    color=icons[member][1],
                )
                for member in Category
            ],
            districts=[member.value for member in District],
            statuses=[
                StatusCode(
                    code=member.value,
                    name=member.label,
                    badge_class=badges[member],
                )
                for member in SpaceStatus
            ],
        )
