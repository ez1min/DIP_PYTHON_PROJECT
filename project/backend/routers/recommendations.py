"""추천 실행과 사용자 추천 이력 API."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.dependencies import CurrentUser, DbSession
from backend.models import (
    RecommendationResult,
    RecommendationRun,
    Space,
    SpaceStatus,
    UserPreference,
)
from backend.recommendation import calculate_suitability, get_active_weight_config
from backend.schemas import (
    RecommendationCriteria,
    RecommendationHistoryResponse,
    RecommendationResponse,
)


router = APIRouter(prefix="/recommendations", tags=["추천"])


@router.post("", response_model=RecommendationResponse)
def create_recommendation(
    criteria: RecommendationCriteria, current_user: CurrentUser, db: DbSession
) -> dict:
    weights = get_active_weight_config(db, criteria.purpose_category)
    preference = db.get(UserPreference, current_user.id)
    if preference is None:
        preference = UserPreference(user_id=current_user.id)
        db.add(preference)
    preference.preferred_district = criteria.preferred_district
    preference.preferred_category = criteria.purpose_category
    preference.max_monthly_rent = criteria.max_monthly_rent
    preference.min_area = criteria.min_area
    preference.parking_required = criteria.parking_required

    spaces = list(
        db.scalars(select(Space).where(Space.status == SpaceStatus.AVAILABLE)).all()
    )
    scored = sorted(
        ((space, calculate_suitability(space, criteria, weights)) for space in spaces),
        key=lambda item: (-item[1].normalized_score, item[0].monthly_rent, item[0].id),
    )[:3]

    run = RecommendationRun(
        user_id=current_user.id,
        weight_config_id=weights.id,
        **criteria.model_dump(),
    )
    db.add(run)
    db.flush()

    results: list[RecommendationResult] = []
    for rank, (space, score) in enumerate(scored, start=1):
        result = RecommendationResult(
            run_id=run.id,
            space_id=space.id,
            rank=rank,
            raw_score=score.raw_score,
            normalized_score=score.normalized_score,
            reasons=score.reasons,
        )
        result.space = space
        db.add(result)
        results.append(result)
    db.commit()

    return {"run_id": run.id, "weight_version": weights.version, "results": results}


@router.get("/me", response_model=list[RecommendationHistoryResponse])
def list_my_recommendations(current_user: CurrentUser, db: DbSession) -> list[dict]:
    statement = (
        select(RecommendationRun)
        .where(RecommendationRun.user_id == current_user.id)
        .options(
            selectinload(RecommendationRun.weight_config),
            selectinload(RecommendationRun.results).selectinload(RecommendationResult.space),
        )
        .order_by(RecommendationRun.created_at.desc())
        .limit(20)
    )
    runs = list(db.scalars(statement).all())
    return [
        {
            "id": run.id,
            "preferred_district": run.preferred_district,
            "purpose_category": run.purpose_category,
            "max_monthly_rent": run.max_monthly_rent,
            "min_area": run.min_area,
            "parking_required": run.parking_required,
            "weight_version": run.weight_config.version,
            "created_at": run.created_at,
            "results": run.results,
        }
        for run in runs
    ]
