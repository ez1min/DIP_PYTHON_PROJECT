"""오프라인 ETL 실행 스크립트.

binzip/DATA/data_elec의 원자료를 공공데이터 API와 대조해
binzip/DATA/spaces.json (FastAPI가 서빙할 캐시)을 만든다.

정부 API 키가 필요하므로 이 스크립트는 서버에서만 실행한다.
FastAPI는 이 스크립트가 만든 JSON만 읽고, 요청마다 정부 API를 부르지 않는다.

실행:
    python -m binzip.build_dataset
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from binzip.pipeline import build_spaces

OUT_DIR = os.path.join(os.path.dirname(__file__), "DATA")
SPACES_PATH = os.path.join(OUT_DIR, "spaces.json")
SYNC_LOG_PATH = os.path.join(OUT_DIR, "sync_logs.json")


def main() -> None:
    spaces = build_spaces()

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(SPACES_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [s.model_dump(by_alias=True, mode="json") for s in spaces],
            f,
            ensure_ascii=False,
            indent=2,
        )

    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": "건축물대장 HUB API + 전기 사용량 원자료",
        "status": "SUCCESS",
        "count": len(spaces),
        "note": f"{len(spaces)}건의 유휴공간 후보를 수집했습니다.",
    }
    logs = []
    if os.path.exists(SYNC_LOG_PATH):
        with open(SYNC_LOG_PATH, encoding="utf-8") as f:
            logs = json.load(f)
    logs.insert(0, log_entry)
    with open(SYNC_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs[:50], f, ensure_ascii=False, indent=2)

    print(f"수집 완료: {len(spaces)}건 -> {SPACES_PATH}")


if __name__ == "__main__":
    main()
