"""Public catalog loading and on-demand database materialization."""

from __future__ import annotations

import json
from functools import lru_cache

from sqlalchemy.orm import Session

from backend.config import PROJECT_DIR
from backend.models import Space as DatabaseSpace
from backend.models import SpaceImage, SpaceStatus as DatabaseSpaceStatus
from binzip.catalog_photos import LEGACY_PLACEHOLDER_PHOTO, curated_placeholder_photos
from binzip.schemas.space import Space as CatalogSpace


CATALOG_PATH = PROJECT_DIR / "binzip" / "DATA" / "spaces.json"


@lru_cache(maxsize=1)
def load_catalog() -> tuple[CatalogSpace, ...]:
    raw_spaces = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    spaces = []
    for sequence, item in enumerate(raw_spaces, start=1):
        space = CatalogSpace.model_validate(item)
        if space.photos == [LEGACY_PLACEHOLDER_PHOTO]:
            space = space.model_copy(update={"photos": curated_placeholder_photos(sequence)})
        spaces.append(space)
    return tuple(spaces)


@lru_cache(maxsize=1)
def catalog_by_id() -> dict[str, CatalogSpace]:
    return {space.id: space for space in load_catalog()}


def ensure_catalog_space(db: Session, space_id: str) -> DatabaseSpace | None:
    """Return a DB space, creating it from the public catalog when necessary."""
    database_space = db.get(DatabaseSpace, space_id)
    if database_space is not None:
        return database_space

    catalog_space = catalog_by_id().get(space_id)
    if catalog_space is None:
        return None

    supported_statuses = {status.value for status in DatabaseSpaceStatus}
    status_value = catalog_space.status.value
    status = (
        DatabaseSpaceStatus(status_value)
        if status_value in supported_statuses
        else DatabaseSpaceStatus.AVAILABLE
    )
    database_space = DatabaseSpace(
        id=catalog_space.id,
        name=catalog_space.name,
        address=catalog_space.address,
        district=catalog_space.district.value,
        category=catalog_space.category.value,
        category_name=catalog_space.category_name,
        area=catalog_space.area,
        deposit=catalog_space.deposit,
        monthly_rent=catalog_space.monthly_rent,
        maintenance_fee=catalog_space.maintenance_fee,
        parking=catalog_space.parking_available,
        parking_spaces=catalog_space.parking_spaces,
        lat=catalog_space.lat,
        lng=catalog_space.lng,
        main_image_url=catalog_space.photos[0],
        description=catalog_space.description or None,
        floor=catalog_space.floor or None,
        building_structure=catalog_space.structure or None,
        remodeling_status=catalog_space.remodeling_status.value,
        remodeling_support=catalog_space.remodeling_support or None,
        managing_agency=catalog_space.managing_agency,
        agency_contact=catalog_space.agency_contact,
        transport_info=catalog_space.transport_info or None,
        utilities=catalog_space.utilities,
        tags=catalog_space.tags,
        features=catalog_space.features,
        source_name="Public building registry and electricity-use catalog",
        status=status,
    )
    database_space.images = [
        SpaceImage(url=url, alt_text=catalog_space.name, sort_order=index)
        for index, url in enumerate(catalog_space.photos)
    ]
    db.add(database_space)
    db.flush()
    return database_space
