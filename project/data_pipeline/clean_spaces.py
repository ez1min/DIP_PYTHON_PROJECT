"""공간 원천 데이터 정제 1차 스크립트.

7일차 범위
- 공백/주소 형식 정리
- 면적과 월 임대료 숫자 변환
- 용도/상태 공통 코드 변환
- 이름+주소 기준 중복 제거
- 필수값이 없는 행을 검수 대기로 분리

외부 데이터 확보 후 확장 항목
- 대구 공공데이터 API 실제 호출
- 필요 시 허용된 대상의 수집기
- 주소만 제공될 경우 좌표 지오코딩

정제 결과의 PostgreSQL 업서트는 import_spaces.py가 담당합니다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "sample_raw.csv"

CATEGORY_CODES = {
    "문화예술": "ART",
    "창업": "STARTUP",
    "작업실": "WORKSHOP",
    "상점": "SHOP",
    "SHOP": "SHOP",
    "사회적기업": "SOCIAL",
    "사무실": "OFFICE",
}

STATUS_CODES = {
    "이용가능": "AVAILABLE",
    "예약중": "RESERVED",
    "리모델링중": "REMODELING",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_number(value: str, *, won_to_manwon: bool = False) -> float | None:
    raw = normalize_text(value).replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        return None
    number = float(match.group())
    if won_to_manwon and "원" in raw and "만원" not in raw:
        number /= 10000
    return round(number, 1)


def clean_row(row: dict[str, str]) -> tuple[dict | None, str | None]:
    name = normalize_text(row.get("name", ""))
    address = normalize_text(row.get("address", ""))
    district = normalize_text(row.get("district", ""))
    area = parse_number(row.get("area", ""))
    rent = parse_number(row.get("rent", ""), won_to_manwon=True)

    if not name or not district or len(address) < 10 or area is None or rent is None:
        return None, "필수값 누락 또는 주소 검수 필요"

    return {
        "source_id": normalize_text(row.get("source_id", "")),
        "name": name,
        "district": district,
        "address": address,
        "area": area,
        "monthly_rent": int(rent) if rent.is_integer() else rent,
        "category": CATEGORY_CODES.get(normalize_text(row.get("category", "")), "UNKNOWN"),
        "status": STATUS_CODES.get(normalize_text(row.get("status", "")), "REVIEW"),
        "data_stage": "CLEANED_PREVIEW",
    }, None


def clean_file(path: Path) -> tuple[list[dict], list[dict]]:
    cleaned: list[dict] = []
    rejected: list[dict] = []
    seen: set[tuple[str, str]] = set()

    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            item, reason = clean_row(row)
            if item is None:
                rejected.append({"source_id": row.get("source_id"), "reason": reason})
                continue

            key = (item["name"], item["address"])
            if key in seen:
                rejected.append({"source_id": item["source_id"], "reason": "중복 공간"})
                continue
            seen.add(key)
            cleaned.append(item)

    return cleaned, rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, help="선택: 정제 미리보기 JSON 저장 경로")
    args = parser.parse_args()

    cleaned, rejected = clean_file(args.input)
    result = {
        "stage": "day7-preview",
        "cleaned_count": len(cleaned),
        "rejected_count": len(rejected),
        "cleaned": cleaned,
        "rejected": rejected,
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(f"saved: {args.output}")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
