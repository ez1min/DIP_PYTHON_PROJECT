"""관리자 전용 신청 검토, 공간 관리, seed 동기화 API."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database import seed_spaces
from backend.dependencies import AdminUser, DbSession
from backend.models import (
    Application,
    ApplicationStatus,
    DataSyncLog,
    Space,
    SpaceImage,
    SyncStatus,
)
from backend.schemas import (
    AdminApplicationResponse,
    ApplicationReview,
    SpaceCreate,
    SpaceSummary,
    SpaceUpdate,
)


router = APIRouter(prefix="/admin", tags=["관리자"])


def _application_response(application: Application) -> dict:
    return {
        "id": application.id,
        "user_id": application.user_id,
        "user_email": application.applicant.email,
        "user_name": application.applicant.name,
        "visit_date": application.visit_date,
        "application_type": application.application_type,
        "applicant_name": application.applicant_name,
        "applicant_phone": application.applicant_phone,
        "message": application.message,
        "status": application.status,
        "reviewed_by": application.reviewed_by,
        "reviewed_at": application.reviewed_at,
        "review_note": application.review_note,
        "cancelled_at": application.cancelled_at,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "space": application.space,
    }


@router.get("/applications", response_model=list[AdminApplicationResponse])
def list_applications(
    _: AdminUser,
    db: DbSession,
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
) -> list[dict]:
    statement = (
        select(Application)
        .options(
            selectinload(Application.applicant),
            selectinload(Application.space).selectinload(Space.images),
        )
        .order_by(Application.created_at.desc())
    )
    if status_filter is not None:
        statement = statement.where(Application.status == status_filter)
    return [_application_response(item) for item in db.scalars(statement).all()]


@router.patch("/applications/{application_id}/review", response_model=AdminApplicationResponse)
def review_application(
    application_id: int,
    payload: ApplicationReview,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    application = db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .options(
            selectinload(Application.applicant),
            selectinload(Application.space).selectinload(Space.images),
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status_code=409, detail="대기 중인 신청만 처리할 수 있습니다.")

    application.status = payload.status
    application.review_note = payload.review_note
    application.reviewed_by = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    return _application_response(application)


def _replace_images(space: Space, images: list) -> None:
    space.images.clear()
    for image in sorted(images, key=lambda item: item.sort_order):
        space.images.append(SpaceImage(**image.model_dump()))
    if images and not space.main_image_url:
        space.main_image_url = sorted(images, key=lambda item: item.sort_order)[0].url


@router.post("/spaces", response_model=SpaceSummary, status_code=status.HTTP_201_CREATED)
def create_space(payload: SpaceCreate, _: AdminUser, db: DbSession) -> Space:
    if db.get(Space, payload.id) is not None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 공간 ID입니다.")
    values = payload.model_dump(exclude={"images"})
    space = Space(**values)
    _replace_images(space, payload.images)
    db.add(space)
    db.commit()
    db.refresh(space)
    return space


@router.patch("/spaces/{space_id}", response_model=SpaceSummary)
def update_space(
    space_id: str, payload: SpaceUpdate, _: AdminUser, db: DbSession
) -> Space:
    space = db.scalar(
        select(Space).where(Space.id == space_id).options(selectinload(Space.images))
    )
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")

    values = payload.model_dump(exclude_unset=True, exclude={"images"})
    for field, value in values.items():
        setattr(space, field, value)
    if payload.images is not None:
        _replace_images(space, payload.images)
    if space.parking is False:
        space.parking_spaces = 0
    db.commit()
    db.refresh(space)
    return space


@router.delete("/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_space(space_id: str, _: AdminUser, db: DbSession) -> Response:
    space = db.get(Space, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")
    if space.applications or space.recommendation_results:
        raise HTTPException(
            status_code=409,
            detail="신청 또는 추천 이력이 있는 공간은 삭제할 수 없습니다. 상태를 변경해주세요.",
        )
    db.delete(space)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/data-sync/seed")
def sync_seed_spaces(_: AdminUser, db: DbSession) -> dict:
    log = DataSyncLog(source="backend/seed_spaces.json", status=SyncStatus.RUNNING)
    db.add(log)
    db.commit()
    db.refresh(log)
    try:
        created = seed_spaces(db)
        total = len(list(db.scalars(select(Space.id)).all()))
        log.status = SyncStatus.SUCCEEDED
        log.finished_at = datetime.now(timezone.utc)
        log.total_count = total
        log.success_count = total
        db.commit()
        return {"status": "SUCCEEDED", "created": created, "total": total}
    except Exception as exc:
        db.rollback()
        log = db.get(DataSyncLog, log.id)
        if log is not None:
            log.status = SyncStatus.FAILED
            log.finished_at = datetime.now(timezone.utc)
            log.error_count = 1
            log.error_message = str(exc)[:2000]
            db.commit()
        raise HTTPException(status_code=500, detail="공간 데이터 동기화에 실패했습니다.") from exc
