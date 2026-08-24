"""공공데이터포털(data.go.kr) API 게이트웨이는 가끔 일시적으로 503/타임아웃을
낸다("SERVICETIMEOUT_ERROR" 등). 재시도 없이 넘기면 그 필지·그 달 데이터를
통째로 놓치므로, 5xx나 네트워크 예외에는 지수 백오프로 재시도한다.
"""

from __future__ import annotations

import time

import requests


def get_with_retry(
    url: str,
    params: dict,
    timeout: int = 10,
    retries: int = 3,
    backoff: float = 1.5,
) -> requests.Response | None:
    """5xx·타임아웃은 재시도, 4xx나 정상 응답은 즉시 반환.

    반환값: requests.Response(상태코드 무관하게, 4xx/정상 응답 시) 또는
    None(재시도까지 다 실패 — 이미 에러를 출력했다).
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:
            if attempt < retries:
                print(f"[요청 예외, {attempt}/{retries}회 후 재시도] {url}: {e}")
                time.sleep(backoff**attempt)
                continue
            print(f"[요청 실패, {retries}회 재시도 후 포기] {url}: {e}")
            return None

        if response.status_code < 500:
            return response

        if attempt < retries:
            print(f"[HTTP {response.status_code}, {attempt}/{retries}회 후 재시도] {url}")
            time.sleep(backoff**attempt)
            continue

        print(f"[HTTP {response.status_code}, {retries}회 재시도 후 포기] {response.text[:200]}")
        return response

    return None
