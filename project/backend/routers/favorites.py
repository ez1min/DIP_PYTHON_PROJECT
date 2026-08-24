"""로그인 사용자의 관심 공간 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.catalog import ensure_catalog_space
from backend.dependencies import CurrentUser, DbSession
from backend.models import Favorite
from backend.schemas import FavoriteResponse


router = APIRouter(prefix="/favorites", tags=["관심 공간"])


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(current_user: CurrentUser, db: DbSession) -> list[Favorite]:
    statement = (
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .options(selectinload(Favorite.space))
        .order_by(Favorite.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post("/{space_id}", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(space_id: str, current_user: CurrentUser, db: DbSession) -> Favorite:
    space = ensure_catalog_space(db, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="해당 공간을 찾을 수 없습니다.")
    favorite = db.get(Favorite, (current_user.id, space_id))
    if favorite is None:
        favorite = Favorite(user_id=current_user.id, space_id=space_id)
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
    favorite.space = space
    return favorite


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(space_id: str, current_user: CurrentUser, db: DbSession) -> Response:
    favorite = db.get(Favorite, (current_user.id, space_id))
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
