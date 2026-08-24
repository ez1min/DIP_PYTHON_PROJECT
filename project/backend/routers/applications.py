"""사용자 방문·이용 신청 API."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.catalog import ensure_catalog_space
from backend.dependencies import CurrentUser, DbSession
from backend.models import Application, ApplicationStatus, SpaceStatus
from backend.schemas import ApplicationCreate, ApplicationResponse


router = APIRouter(prefix="/applications", tags=["신청"])


@router.get("/me", response_model=list[ApplicationResponse])
def list_my_applications(current_user: CurrentUser, db: DbSession) -> list[Application]:
    statement = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .options(selectinload(Application.space))
        .order_by(Application.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate, current_user: CurrentUser, db: DbSession
) -> Application:
    space = ensure_catalog_space(db, payload.space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")
    if space.status != SpaceStatus.AVAILABLE:
        raise HTTPException(status_code=409, detail="현재 신청할 수 없는 공간입니다.")
    if payload.visit_date < date.today():
        raise HTTPException(status_code=422, detail="과거 날짜로는 신청할 수 없습니다.")

    duplicate = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.space_id == payload.space_id,
            Application.visit_date == payload.visit_date,
            Application.status.in_([ApplicationStatus.PENDING, ApplicationStatus.APPROVED]),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="같은 날짜에 이미 신청한 공간입니다.")

    application = Application(user_id=current_user.id, **payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    application.space = space
    return application


@router.patch("/{application_id}/cancel", response_model=ApplicationResponse)
def cancel_application(
    application_id: int, current_user: CurrentUser, db: DbSession
) -> Application:
    application = db.scalar(
        select(Application)
        .where(Application.id == application_id, Application.user_id == current_user.id)
        .options(selectinload(Application.space))
    )
    if application is None:
        raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status_code=409, detail="검토 중인 신청만 취소할 수 있습니다.")

    application.status = ApplicationStatus.CANCELLED
    application.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    return application
