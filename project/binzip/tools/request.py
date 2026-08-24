import time
from .http_retry import get_with_retry
from .util import util
from pandas import DataFrame
import pandas as pd


class request:
    def __init__(self) -> None:

        self.BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"

        # 가격 조회       # 면적, 주차 여부, 건폐율 등등
        self.END_POINT_URL = ("/getBrHsprcInfo", "/getBrTitleInfo")

        self.PARCEL_PARAM_MAP = {
            "SGG_CD": ("sigunguCd", 5),  # 시군구코드
            "STDG_CD": ("bjdongCd", 5),  # 법정동코드
            "MNO": ("bun", 4),  # 번
            "SNO": ("ji", 4),  # 지
        }

        self.utils = util()

    def get_point_xy(
        self,
        address: str,
        API_KEY: str,
        addr_type: str = "road",
        apiurl: str = "https://api.vworld.kr/req/address",
        timeout: int = 10,
    ):
        """주소를 좌표로 변환. 실패하면 None, 성공하면 (lat, lng) 반환.

        addr_type="road"는 도로명주소(newPlatPlc), "parcel"은 지번주소(platPlc/PLOT_PSTN)용.
        주소 형식과 type이 어긋나면 VWorld가 조용히 실패 응답을 준다.
        """
        params = {
            "service": "address",
            "request": "getcoord",
            "crs": "epsg:4326",
            "address": address,
            "format": "json",
            "type": addr_type,
            "key": API_KEY,
        }
        response = get_with_retry(apiurl, params, timeout=timeout)
        if response is None:
            return None

        try:
            payload = response.json()
        except ValueError:
            print(f"[지오코딩 JSON 아님] {address}: {response.text[:200]}")
            return None

        if payload.get("response", {}).get("status") != "OK":
            return None

        point = payload["response"]["result"]["point"]
        return float(point["y"]), float(point["x"])  # (lat, lng)

    # 건축물 대장 정보
    def get_Building_Register(
        self,
        sigunguCd: str,
        bjdongCd: str,
        bun: str,
        ji: str,
        API_KEY: str,
        numOfRows: int = 100,
        timeout: int = 10,
        URL: str = "",
    ):
        """필지 코드 하나로 건축물대장을 조회. 실패하면 None을 반환하고 사유를 출력한다."""

        params = {
            "serviceKey": API_KEY,  # 공공데이터포털에서 받은 인증키
            "sigunguCd": self.utils.pad_code(sigunguCd, 5),  # 시군구코드
            "bjdongCd": self.utils.pad_code(bjdongCd, 5),  # 법정동코드
            "bun": self.utils.pad_code(bun, 4),
            "ji": self.utils.pad_code(ji, 4),
            "_type": "json",
            "numOfRows": numOfRows,
        }

        response = get_with_retry(URL, params, timeout=timeout)
        if response is None:
            return None

        if response.status_code != 200:
            # data.go.kr은 인증 오류도 본문에 사유를 담아 보낸다
            print(f"[HTTP {response.status_code}] {response.text[:200]}")
            return None

        try:
            return response.json()
        except ValueError:
            print(f"[JSON 아님] {response.text[:200]}")
            return None

    def extract_items(self, payload):
        """응답에서 item 목록만 꺼낸다. 결과가 1건이면 dict, 여러 건이면 list로 온다."""
        if not payload:
            return []
        body = payload.get("response", {}).get("body", {})
        items = (body.get("items") or {}).get("item")
        if items is None:
            return []
        return items if isinstance(items, list) else [items]

    def fetch_building_registers(
        self, df: DataFrame, API_KEY: str, delay: float = 0.1, URL: str = ""
    ) -> DataFrame:
        """df의 필지 코드 4개로 건축물대장을 조회해 DataFrame으로 반환.
        조회 대상은 URL로 넘긴 엔드포인트(표제부/주택가격 등)를 따른다.
        같은 필지가 여러 행(월별 사용량)에 걸쳐 있으므로 중복은 한 번만 호출한다.
        """

        code_cols = list(self.PARCEL_PARAM_MAP)
        missing = [c for c in code_cols if c not in df.columns]
        if missing:
            raise KeyError(f"필요한 컬럼 없음: {missing}")

        rows = []
        for codes in df[code_cols].drop_duplicates().itertuples(index=False):
            sgg, stdg, mno, sno = codes
            payload = self.get_Building_Register(sgg, stdg, mno, sno, API_KEY, URL=URL)
            for item in self.extract_items(payload):
                rows.append({**dict(zip(code_cols, codes)), **item})
            if delay:
                time.sleep(delay)

        return pd.DataFrame(rows)
