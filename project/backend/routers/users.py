"""현재 사용자와 관리자용 사용자 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.dependencies import AdminUser, CurrentUser, DbSession
from backend.models import User, UserPreference
from backend.schemas import (
    AccountDeactivate,
    PasswordChange,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
    UserUpdate,
)
from backend.security import hash_password, verify_password


router = APIRouter(prefix="/users", tags=["사용자"])
admin_router = APIRouter(prefix="/admin/users", tags=["관리자"])


@router.get("/me", response_model=UserResponse)
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> User:
    current_user.name = payload.name
    current_user.phone = payload.phone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/password")
def change_password(payload: PasswordChange, current_user: CurrentUser, db: DbSession) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}


@router.post("/me/deactivate")
def deactivate_account(payload: AccountDeactivate, current_user: CurrentUser, db: DbSession) -> dict:
    if current_user.role.value == "ADMIN":
        raise HTTPException(status_code=409, detail="관리자 계정은 운영 설정에서 비활성화해야 합니다.")
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="비밀번호가 올바르지 않습니다.")
    current_user.is_active = False
    db.commit()
    return {"status": "ok"}


def get_or_create_preference(db: DbSession, user_id: int) -> UserPreference:
    preference = db.get(UserPreference, user_id)
    if preference is None:
        preference = UserPreference(user_id=user_id)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    return preference


@router.get("/me/preferences", response_model=UserPreferenceResponse)
def read_preferences(current_user: CurrentUser, db: DbSession) -> UserPreference:
    return get_or_create_preference(db, current_user.id)


@router.put("/me/preferences", response_model=UserPreferenceResponse)
def update_preferences(
    payload: UserPreferenceUpdate, current_user: CurrentUser, db: DbSession
) -> UserPreference:
    preference = get_or_create_preference(db, current_user.id)
    for field, value in payload.model_dump().items():
        setattr(preference, field, value)
    db.commit()
    db.refresh(preference)
    return preference


@admin_router.get("", response_model=list[UserResponse])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())
