import os, glob, json
import pandas as pd
from pandas import DataFrame

# binzip/ 디렉터리. 실행 위치와 무관하게 데이터 경로를 잡기 위한 기준점.
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class util:
    def __init__(self) -> None:
        pass

    def get_data_dir(self):
        data_dir = os.path.join(PACKAGE_DIR, "DATA", "data_elec")
        return sorted(glob.glob(os.path.join(data_dir, "*.json")))  # .DS_Store 제외

    def load_df(self, path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return pd.DataFrame(raw["Data"])

    def filter(self, Kwh: int, df: DataFrame):
        return df[df["USGQTY"] <= Kwh]

    def pad_code(self, value, width: int):
        """'71' -> '0071'. 코드값은 앞자리 0이 살아 있어야 API가 인식한다."""
        if value is None or pd.isna(value):
            return None
        return str(value).strip().zfill(width)
