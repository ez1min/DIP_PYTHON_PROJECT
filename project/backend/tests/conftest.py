from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


# backend 모듈을 import하기 전에 격리된 DB와 테스트용 키를 설정한다.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-integration-tests"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@example.com"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin-password-1234"
os.environ["BOOTSTRAP_ADMIN_NAME"] = "테스트 관리자"

from backend.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
