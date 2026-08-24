"""Read-only API for the public-space dataset built by the binzip pipeline."""

from __future__ import annotations

from fastapi import APIRouter

from backend.catalog import load_catalog
from binzip.schemas.space import CommonCodes, Space


router = APIRouter(prefix="/catalog", tags=["공개 공간 카탈로그"])
@router.get("/spaces", response_model=list[Space])
def list_catalog_spaces() -> tuple[Space, ...]:
    """Return the latest validated binzip result in the frontend contract."""
    return load_catalog()


@router.get("/common-codes", response_model=CommonCodes)
def get_common_codes() -> CommonCodes:
    return CommonCodes.default()
