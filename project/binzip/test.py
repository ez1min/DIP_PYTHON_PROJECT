from .tools.request import request
from .tools.util import util
from dotenv import load_dotenv
from pathlib import Path
import os

# 실행 위치가 아니라 이 파일 옆의 .env를 읽는다.
load_dotenv(Path(__file__).parent / ".env")
GOV_API_KEY = os.environ["GOVDATA_DEC"]
VWORLD_API_KEY = os.environ["VWORLD"]

utils = util()
requests = request()

# 빈집 필터링 -> 필지별 건축물대장 조회
for f in utils.get_data_dir():
    df = utils.load_df(f)
    if not set(requests.PARCEL_PARAM_MAP).issubset(df.columns):
        print(f"건너뜀(코드 컬럼 없음): {os.path.basename(f)}")
        continue

    df_filtered = utils.filter(5, df)

    for END_POINT in requests.END_POINT_URL:
        # os.path.join은 URL용이 아니다. "/..."로 시작하면 앞부분을 버린다.
        URL = requests.BASE_URL + END_POINT
        print(f"{os.path.basename(f)}: 빈집 후보 {len(df_filtered)}행")
        register_df = requests.fetch_building_registers(df_filtered, GOV_API_KEY, URL=URL)
        print("=" * 3, END_POINT, "=" * 3)
        print(register_df.to_json(), "\n")
