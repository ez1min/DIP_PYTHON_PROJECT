"""국토교통부 실거래가 공개시스템에서 상업업무용·공장창고용 매매를 가져와
지번으로 필지와 매칭한다.

두 엔드포인트를 다 부르는 이유: 건축물 주용도로 상업/공장을 구분하는
category 휴리스틱(pipeline.guess_category)이 완벽하지 않다. 카테고리를 믿고
한쪽만 불렀다가 오분류로 못 찾느니, 둘 다 불러 인메모리에서 매칭하는 편이
안전하다. API 호출은 (시군구 x 월) 단위라 필지 수와 무관하게 한 번만 하면
된다 — 응답에 지번 필터가 없어서 해당 시군구·월의 모든 거래가 한꺼번에 온다.

한계: 실거래가 공개시스템은 '일반'(단독 소유) 건물의 지번을 개인정보 보호
목적으로 일부 마스킹해서 내려준다(예: "1***"). 마스킹된 지번은 특정 필지와
확실히 매칭할 수 없으므로 매칭 대상에서 제외한다 — 즉 우리가 찾는 건물이
실제로 거래됐어도 마스킹돼 있으면 놓칠 수 있다. 이건 데이터 자체의 한계이지
코드 버그가 아니다. 아파트(집합건물)는 지번이 마스킹되지 않지만, 이 파이프라인이
다루는 건물 대부분은 단독 소유 근린생활시설/공장이라 END_POINT_APT는 기본
파이프라인에서 쓰지 않는다(필요하면 TRADE_SOURCES에 추가).
"""

from __future__ import annotations

import re
import time
from datetime import date
from typing import Iterable

from binzip.schemas import DealType, TransactionInfo
from binzip.tools.http_retry import get_with_retry

END_POINT_APT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
END_POINT_NRG = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
END_POINT_INDU = "https://apis.data.go.kr/1613000/RTMSDataSvcInduTrade/getRTMSDataSvcInduTrade"

TRADE_SOURCES = [
    (END_POINT_NRG, "국토부 실거래가(상업업무용)"),
    (END_POINT_INDU, "국토부 실거래가(공장·창고용)"),
]

_PLATPLC_RE = re.compile(r"([가-힣0-9]+(?:동|가|리))\s*(\d+(?:-\d+)?)\s*번지")

TradeKey = tuple[str, str, str]  # (sggCd, dongName, jibun)


def parse_dong_jibun(plat_plc: str) -> tuple[str, str] | None:
    """지번주소(platPlc)에서 (동이름, 지번)을 추출. 실패하면 None.

    예: "대구광역시 수성구 삼덕동 458-3번지" -> ("삼덕동", "458-3")
    """
    m = _PLATPLC_RE.search(plat_plc or "")
    if not m:
        return None
    return m.group(1), m.group(2)


def is_masked(jibun: str) -> bool:
    return "*" in jibun


def _parse_amount(raw: str) -> int:
    """"108,000" -> 108000. 만원 단위 문자열에 콤마가 섞여 온다."""
    return int(str(raw).replace(",", "").strip())


def _fetch_month(url: str, sgg_cd: str, deal_ymd: str, api_key: str, timeout: int = 10) -> list[dict]:
    """(시군구, 월) 하나의 거래 전체를 가져온다.

    이 API는 지번으로 거르는 파라미터가 없다 — 한 번 호출로 그 시군구의
    그 달 거래가 전부 온다. 그래서 필지별로 부르지 않고 시군구 단위로 한 번만
    불러 인메모리 인덱스를 만든다.
    """
    params = {
        "LAWD_CD": sgg_cd,
        "DEAL_YMD": deal_ymd,
        "serviceKey": api_key,
        "_type": "json",
        "numOfRows": 999,
    }
    response = get_with_retry(url, params, timeout=timeout)
    if response is None:
        return []

    try:
        body = response.json()["response"]["body"]
    except (ValueError, KeyError):
        print(f"[실거래가 JSON 아님] {url} {sgg_cd} {deal_ymd}: {response.text[:200]}")
        return []

    if not body.get("totalCount"):
        return []
    items = body["items"]["item"]
    return items if isinstance(items, list) else [items]


def _months_back(n: int) -> list[str]:
    """오늘부터 과거 n개월의 YYYYMM 목록."""
    months = []
    year, month = date.today().year, date.today().month
    for _ in range(n):
        months.append(f"{year:04d}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months


def build_trade_index(
    sgg_codes: Iterable[str],
    api_key: str,
    months_back: int = 24,
    delay: float = 0.15,
) -> dict[TradeKey, TransactionInfo]:
    """(시군구, 동이름, 지번) -> 최근 거래 인덱스를 만든다.

    지번이 마스킹된("1***") 항목은 키를 만들 수 없어 제외한다.
    같은 필지가 여러 번 거래됐으면 가장 최근 거래만 남긴다.
    """
    index: dict[TradeKey, TransactionInfo] = {}
    sgg_codes = sorted(set(sgg_codes))
    months = _months_back(months_back)
    total_calls = len(sgg_codes) * len(months) * len(TRADE_SOURCES)
    print(f"실거래가 조회: 시군구 {len(sgg_codes)}개 x {months_back}개월 x 엔드포인트 {len(TRADE_SOURCES)}개 = 최대 {total_calls}회 호출")

    for sgg in sgg_codes:
        for ymd in months:
            for url, source in TRADE_SOURCES:
                items = _fetch_month(url, sgg, ymd, api_key)
                if delay:
                    time.sleep(delay)
                for item in items:
                    jibun = str(item.get("jibun", "")).strip()
                    dong = str(item.get("umdNm", "")).strip()
                    if not dong or not jibun or is_masked(jibun):
                        continue
                    try:
                        amount = _parse_amount(item["dealAmount"])
                        deal_date = date(int(item["dealYear"]), int(item["dealMonth"]), int(item["dealDay"]))
                    except (KeyError, ValueError):
                        continue

                    key = (sgg, dong, jibun)
                    candidate = TransactionInfo(
                        deal_type=DealType.SALE,
                        deal_amount=amount,
                        deal_date=deal_date,
                        building_use=str(item.get("buildingUse", "")).strip(),
                        source=source,
                    )
                    existing = index.get(key)
                    if existing is None or candidate.deal_date > existing.deal_date:
                        index[key] = candidate

    print(f"실거래가 인덱스: 매칭 가능한(비마스킹) 거래 {len(index)}건")
    return index


def lookup_transaction(
    index: dict[TradeKey, TransactionInfo], sgg_cd: str, dong: str, jibun: str
) -> TransactionInfo | None:
    return index.get((sgg_cd, dong, jibun))
