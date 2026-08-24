"""검수된 공간 CSV를 PostgreSQL에 안전하게 upsert한다.

기본 실행은 검증만 수행한다. 실제 저장은 --commit 옵션을 명시해야 한다.
여러 값은 파이프(|)로 구분한다: images, utilities, features, tags.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from backend.database import SessionLocal
from backend.models import DataSyncLog, Space, SpaceImage, SyncStatus
from backend.schemas import SpaceCreate


def split_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split("|") if item.strip()]


def optional(value: str | None) -> str | None:
    stripped = (value or "").strip()
    return stripped or None


def parse_row(row: dict[str, str]) -> SpaceCreate:
    image_urls = split_values(row.get("images"))
    return SpaceCreate(
        id=row.get("id", "").strip(),
        name=row.get("name", "").strip(),
        address=row.get("address", "").strip(),
        district=row.get("district", "").strip(),
        category=row.get("category", "").strip(),
        category_name=row.get("category_name", "").strip(),
        area=float(row.get("area", 0)),
        deposit=int(row.get("deposit") or 0),
        monthly_rent=int(row.get("monthly_rent") or 0),
        maintenance_fee=int(row.get("maintenance_fee") or 0),
        parking=(row.get("parking", "").strip().lower() in {"true", "1", "y", "yes", "o"}),
        parking_spaces=int(row.get("parking_spaces") or 0),
        lat=float(row.get("lat", 0)),
        lng=float(row.get("lng", 0)),
        main_image_url=optional(row.get("main_image_url")) or (image_urls[0] if image_urls else None),
        description=optional(row.get("description")),
        floor=optional(row.get("floor")),
        building_structure=optional(row.get("building_structure")),
        remodeling_status=optional(row.get("remodeling_status")),
        remodeling_support=optional(row.get("remodeling_support")),
        managing_agency=optional(row.get("managing_agency")),
        agency_contact=optional(row.get("agency_contact")),
        transport_info=optional(row.get("transport_info")),
        utilities=split_values(row.get("utilities")),
        features=split_values(row.get("features")),
        tags=split_values(row.get("tags")),
        source_name=optional(row.get("source_name")),
        source_url=optional(row.get("source_url")),
        status=(row.get("status") or "AVAILABLE").strip(),
        images=[
            {"url": url, "alt_text": f"{row.get('name', '').strip()} 이미지 {index + 1}", "sort_order": index}
            for index, url in enumerate(image_urls)
        ],
    )


def load_and_validate(path: Path) -> tuple[list[SpaceCreate], list[str]]:
    items: list[SpaceCreate] = []
    errors: list[str] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for line_number, row in enumerate(csv.DictReader(stream), start=2):
            try:
                item = parse_row(row)
                if item.id in seen:
                    raise ValueError(f"중복 공간 ID: {item.id}")
                seen.add(item.id)
                items.append(item)
            except (ValueError, ValidationError) as exc:
                errors.append(f"{line_number}행: {exc}")
    return items, errors


def upsert(items: list[SpaceCreate], source: str) -> tuple[int, int]:
    with SessionLocal() as db:
        log = DataSyncLog(source=source, status=SyncStatus.RUNNING, total_count=len(items))
        db.add(log)
        db.flush()
        created = 0
        updated = 0
        for item in items:
            space = db.scalar(
                select(Space).where(Space.id == item.id).options(selectinload(Space.images))
            )
            values = item.model_dump(exclude={"images"})
            if space is None:
                space = Space(**values)
                db.add(space)
                created += 1
            else:
                for field, value in values.items():
                    if field != "id":
                        setattr(space, field, value)
                updated += 1
            space.images.clear()
            for image in item.images:
                space.images.append(SpaceImage(**image.model_dump()))

        log.status = SyncStatus.SUCCEEDED
        log.finished_at = datetime.now(timezone.utc)
        log.success_count = len(items)
        db.commit()
        return created, updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--commit", action="store_true", help="검증 후 실제 DB에 저장")
    args = parser.parse_args()
    items, errors = load_and_validate(args.csv_path)
    print(f"검증 성공: {len(items)}건, 오류: {len(errors)}건")
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    if not args.commit:
        print("dry-run 완료. 저장하려면 --commit 옵션을 추가하세요.")
        return
    created, updated = upsert(items, args.csv_path.name)
    print(f"DB 저장 완료: 신규 {created}건, 수정 {updated}건")


if __name__ == "__main__":
    main()
