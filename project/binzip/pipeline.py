"""전기 사용량 + 건축물대장 공공데이터를 Space 스키마로 조립하는 오프라인 ETL.

흐름:
  data_elec(*.json) --filter(저사용량=빈집 후보)--> 필지 코드
    --getBrTitleInfo--> 건축물 표제부
    --VWorld geocode--> 좌표
    --매핑--> Space

임대료·보증금·사진·설명 등은 공공데이터에 없다. 실제 값을 지어내지 않고
"정보 없음"류 플레이스홀더로 채우며, 어떤 필드가 플레이스홀더인지는
description에 명시한다. 프론트가 이 값을 그대로 상거래 정보처럼 보여주면
사용자를 오도하므로, 실제 서비스에서는 이 필드들을 채울 별도 데이터 소스
(임대 정보 크롤링, 관리기관 입력 등)가 필요하다.
"""

from __future__ import annotations

import os
import re
import time
from datetime import date

from dotenv import load_dotenv

from binzip import trade
from binzip.schemas import Category, District, Space, TransactionInfo
from binzip.tools.request import request
from binzip.tools.util import util

PLACEHOLDER_PHOTO = (
    "https://images.unsplash.com/photo-1494526585095-c41746248156"
    "?auto=format&fit=crop&w=1000&q=80"
)

# 건축물 주용도 텍스트 -> 프론트 카테고리 코드 휴리스틱.
# 공공데이터에 카테고리 개념이 없어 주용도명 키워드로 근사한다.
_CATEGORY_KEYWORDS: list[tuple[str, Category]] = [
    ("공장", Category.WORKSHOP),
    ("창고", Category.WORKSHOP),
    ("작업장", Category.WORKSHOP),
    ("근린생활", Category.SHOP),
    ("판매", Category.SHOP),
    ("소매", Category.SHOP),
    ("업무", Category.OFFICE),
    ("사무소", Category.OFFICE),
    ("문화", Category.ART),
    ("공연", Category.ART),
    ("전시", Category.ART),
    ("종교", Category.ART),
    ("복지", Category.SOCIAL),
    ("사회", Category.SOCIAL),
    ("교육", Category.SOCIAL),
]

_DISTRICT_NAMES = {d.value for d in District}


def guess_category(main_purpose_name: str) -> Category:
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in (main_purpose_name or ""):
            return category
    return Category.OFFICE


def parse_district(address: str) -> District | None:
    for token in re.findall(r"\S+", address or ""):
        if token in _DISTRICT_NAMES:
            return District(token)
    return None


def build_floor_text(item: dict) -> str:
    ground = int(item.get("grndFlrCnt") or 0)
    under = int(item.get("ugrndFlrCnt") or 0)
    parts = []
    if ground:
        parts.append(f"지상 {ground}층")
    if under:
        parts.append(f"지하 {under}층")
    return " · ".join(parts) if parts else ""


def count_parking(item: dict) -> int:
    keys = ["indrMechUtcnt", "oudrMechUtcnt", "indrAutoUtcnt", "oudrAutoUtcnt"]
    return sum(int(item.get(k) or 0) for k in keys)


def find_transaction(item: dict, trade_index: dict) -> TransactionInfo | None:
    """건축물대장 item의 지번주소(platPlc)로 실거래가 인덱스에서 거래를 찾는다.

    지번이 마스킹된 거래는 애초에 trade_index에 안 들어있으므로, 실제로
    거래가 있었어도 마스킹 때문에 None이 나올 수 있다(trade.py 참고).
    """
    plat_plc = item.get("platPlc") or ""
    parsed = trade.parse_dong_jibun(plat_plc)
    if parsed is None:
        return None
    dong, jibun = parsed
    sgg_cd = item.get("sigunguCd") or ""
    return trade.lookup_transaction(trade_index, sgg_cd, dong, jibun)


def map_to_space(item: dict, seq: int, geocode, trade_index: dict | None = None) -> Space | None:
    """건축물대장 item(getBrTitleInfo) 하나를 Space로 변환. 지오코딩 실패 시 None."""

    address = (item.get("newPlatPlc") or "").strip()
    addr_type = "road"
    if not address:
        address = (item.get("platPlc") or "").strip()
        addr_type = "parcel"
    if not address:
        print(f"[스킵] 주소 없음: mgmBldrgstPk={item.get('mgmBldrgstPk')}")
        return None

    point = geocode(address, addr_type)
    if point is None and addr_type == "road":
        # 도로명주소 지오코딩 실패 시 지번주소로 재시도.
        fallback_addr = (item.get("platPlc") or "").strip()
        if fallback_addr:
            point = geocode(fallback_addr, "parcel")
    if point is None:
        print(f"[스킵] 지오코딩 실패: {address}")
        return None
    lat, lng = point

    district = parse_district(address)
    if district is None:
        print(f"[스킵] 구·군 파싱 실패: {address}")
        return None

    main_purpose = item.get("mainPurpsCdNm") or ""
    category = guess_category(main_purpose)
    area = item.get("totArea")
    if not area or float(area) <= 0:
        print(f"[스킵] 전용면적 없음: {address}")
        return None

    parking_count = count_parking(item)
    last_transaction = find_transaction(item, trade_index) if trade_index else None

    return Space(
        id=f"SPC-P{seq:03d}",
        name=f"{district.value} 유휴 건축물 ({main_purpose or '용도 미상'})",
        category=category,
        district=district,
        address=address,
        lat=lat,
        lng=lng,
        area=float(area),
        deposit=0,
        monthly_rent=0,
        maintenance_fee=0,
        status="AVAILABLE",
        remodeling_status="NONE",
        remodeling_support="",
        managing_agency="정보 없음 (공공데이터 미제공)",
        agency_contact="-",
        photos=[PLACEHOLDER_PHOTO],
        floor=build_floor_text(item),
        structure=item.get("strctCdNm") or "",
        parking=parking_count > 0,
        parking_spaces=parking_count,
        utilities=[],
        transport_info="",
        tags=[t for t in [item.get("strctCdNm"), main_purpose] if t],
        description=(
            "국토교통부 건축물대장(표제부) 기준 자동 수집 정보입니다. "
            "전기 사용량이 낮은 필지를 빈집 후보로 선별했으며, "
            "임대료·보증금·사진·상세 설명은 아직 실제 데이터가 연결되지 않아 "
            "표시되지 않습니다."
        ),
        features=[],
        created_at=date.today(),
        views=0,
        favorite_count=0,
        last_transaction=last_transaction,
    )


def collect_candidate_parcels(utils: util, code_cols: list[str], kwh_threshold: int) -> list[tuple]:
    """저사용량 필지 코드를 API 호출 없이 전부 모은다. 실거래가 인덱스를
    시군구 단위로 미리 만들려면 필지를 조회하기 전에 시군구 목록부터 알아야 한다."""
    seen: set[tuple] = set()
    parcels: list[tuple] = []
    for path in utils.get_data_dir():
        df = utils.load_df(path)
        if not set(code_cols).issubset(df.columns):
            continue
        candidates = utils.filter(kwh_threshold, df)
        for codes in candidates[code_cols].drop_duplicates().itertuples(index=False):
            key = tuple(codes)
            if key not in seen:
                seen.add(key)
                parcels.append(key)
    return parcels


def build_spaces(
    kwh_threshold: int = 5,
    delay: float = 0.1,
    trade_months_back: int = 24,
) -> list[Space]:
    """DATA/data_elec의 저사용량 필지를 건축물대장·실거래가와 대조해 Space 목록을 만든다."""

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    gov_key = os.environ["GOVDATA_DEC"]
    vworld_key = os.environ["VWORLD"]

    utils = util()
    req = request()
    title_url = req.BASE_URL + "/getBrTitleInfo"

    def geocode(address: str, addr_type: str):
        result = req.get_point_xy(address, vworld_key, addr_type=addr_type)
        if delay:
            time.sleep(delay)
        return result

    code_cols = list(req.PARCEL_PARAM_MAP)
    candidate_parcels = collect_candidate_parcels(utils, code_cols, kwh_threshold)

    # 실거래가는 (시군구, 월) 단위로만 조회 가능하다 — 필지 수와 무관하게
    # 시군구 종류만큼만 부르고, 매칭은 아래에서 인메모리로 한다.
    sgg_codes = {p[0] for p in candidate_parcels}
    trade_index = trade.build_trade_index(sgg_codes, gov_key, months_back=trade_months_back)

    spaces: list[Space] = []
    seq = 1
    for sgg, stdg, mno, sno in candidate_parcels:
        payload = req.get_Building_Register(sgg, stdg, mno, sno, gov_key, URL=title_url)
        if delay:
            time.sleep(delay)

        for item in req.extract_items(payload):
            space = map_to_space(item, seq, geocode, trade_index)
            if space is not None:
                spaces.append(space)
                seq += 1

    return spaces
