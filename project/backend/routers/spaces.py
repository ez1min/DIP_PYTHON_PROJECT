"""DB 기반 공간 목록과 상세 조회 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from backend.dependencies import CurrentUser, DbSession
from backend.models import Space, UserPreference
from backend.recommendation import (
    calculate_suitability,
    criteria_from_preference,
    get_active_weight_config,
    preference_is_complete,
)
from backend.schemas import SpaceListResponse, SpaceSummary, SuitabilityResponse


router = APIRouter(prefix="/spaces", tags=["공간"])


@router.get("", response_model=SpaceListResponse)
def list_spaces(
    db: DbSession,
    district: str | None = None,
    category: str | None = None,
    max_rent: int | None = Query(default=None, ge=0),
    min_area: float | None = Query(default=None, ge=0),
    parking: bool | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    query: str | None = Query(default=None, alias="q", max_length=100),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SpaceListResponse:
    filters = []
    if district:
        filters.append(Space.district == district)
    if category:
        filters.append(Space.category == category)
    if max_rent is not None:
        filters.append(Space.monthly_rent <= max_rent)
    if min_area is not None:
        filters.append(Space.area >= min_area)
    if parking is not None:
        filters.append(Space.parking.is_(parking))
    if status_filter:
        filters.append(Space.status == status_filter)
    if query:
        keyword = f"%{query.strip()}%"
        filters.append(
            or_(
                Space.name.ilike(keyword),
                Space.address.ilike(keyword),
                Space.description.ilike(keyword),
                Space.category_name.ilike(keyword),
            )
        )

    total = db.scalar(select(func.count()).select_from(Space).where(*filters)) or 0
    spaces = list(
        db.scalars(
            select(Space)
            .where(*filters)
            .options(selectinload(Space.images))
            .order_by(Space.id)
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return SpaceListResponse(total=total, items=spaces)


@router.get("/{space_id}/suitability", response_model=SuitabilityResponse)
def get_space_suitability(
    space_id: str, current_user: CurrentUser, db: DbSession
) -> SuitabilityResponse:
    space = db.get(Space, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")
    preference = db.get(UserPreference, current_user.id)
    if not preference_is_complete(preference):
        return SuitabilityResponse(space_id=space_id, profile_complete=False)

    criteria = criteria_from_preference(preference)
    weights = get_active_weight_config(db, criteria.purpose_category)
    score = calculate_suitability(space, criteria, weights)
    return SuitabilityResponse(
        space_id=space_id,
        profile_complete=True,
        normalized_score=score.normalized_score,
        raw_score=score.raw_score,
        weight_version=weights.version,
        reasons=score.reasons,
    )


@router.get("/{space_id}", response_model=SpaceSummary)
def get_space(space_id: str, db: DbSession) -> Space:
    space = db.scalar(
        select(Space).where(Space.id == space_id).options(selectinload(Space.images))
    )
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")
    return space
