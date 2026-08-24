"""PPT 규칙 기반 추천 점수 계산 서비스."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import RecommendationWeightConfig, Space, UserPreference
from backend.schemas import RecommendationCriteria


@dataclass(frozen=True)
class SuitabilityScore:
    raw_score: int
    normalized_score: int
    reasons: list[str]


def preference_is_complete(preference: UserPreference | None) -> bool:
    return bool(
        preference
        and preference.preferred_category
        and preference.max_monthly_rent is not None
        and preference.min_area is not None
    )


def criteria_from_preference(preference: UserPreference) -> RecommendationCriteria:
    return RecommendationCriteria(
        preferred_district=preference.preferred_district or "ALL",
        purpose_category=preference.preferred_category or "",
        max_monthly_rent=preference.max_monthly_rent or 0,
        min_area=preference.min_area or 0,
        parking_required=preference.parking_required,
    )


def get_active_weight_config(
    db: Session, purpose_category: str | None = None
) -> RecommendationWeightConfig:
    if purpose_category:
        purpose_config = db.scalar(
            select(RecommendationWeightConfig)
            .where(
                RecommendationWeightConfig.is_active.is_(True),
                RecommendationWeightConfig.purpose_category == purpose_category,
            )
            .order_by(RecommendationWeightConfig.id.desc())
        )
        if purpose_config is not None:
            return purpose_config

    config = db.scalar(
        select(RecommendationWeightConfig)
        .where(
            RecommendationWeightConfig.is_active.is_(True),
            RecommendationWeightConfig.purpose_category.is_(None),
        )
        .order_by(RecommendationWeightConfig.id.desc())
    )
    if config is None:
        raise RuntimeError("활성화된 추천 가중치 설정이 없습니다.")
    return config


def calculate_suitability(
    space: Space,
    criteria: RecommendationCriteria,
    weights: RecommendationWeightConfig,
) -> SuitabilityScore:
    raw_score = weights.base_score
    reasons: list[str] = []

    if criteria.preferred_district == "ALL" or space.district == criteria.preferred_district:
        raw_score += weights.district_weight
        reasons.append(
            "대구 전역 조건" if criteria.preferred_district == "ALL" else "선호 지역 일치"
        )
    if space.category == criteria.purpose_category:
        raw_score += weights.category_weight
        reasons.append("활용 용도 적합")
    if space.monthly_rent <= criteria.max_monthly_rent:
        raw_score += weights.budget_weight
        reasons.append("월 예산 이내")
    elif space.monthly_rent <= criteria.max_monthly_rent + 10:
        raw_score += weights.near_budget_weight
        reasons.append("예산과 10만원 이내")
    if space.area >= criteria.min_area:
        raw_score += weights.area_weight
        reasons.append("최소 면적 충족")
    if criteria.parking_required:
        if space.parking:
            raw_score += weights.parking_weight
            reasons.append("주차 가능")
        parking_max = weights.parking_weight
    else:
        raw_score += weights.parking_optional_weight
        parking_max = weights.parking_optional_weight

    max_score = (
        weights.base_score
        + weights.district_weight
        + weights.category_weight
        + weights.budget_weight
        + weights.area_weight
        + parking_max
    )
    normalized = round((raw_score / max_score) * 100) if max_score else 0
    normalized = min(normalized, weights.score_cap, 100)
    return SuitabilityScore(raw_score=raw_score, normalized_score=normalized, reasons=reasons)
