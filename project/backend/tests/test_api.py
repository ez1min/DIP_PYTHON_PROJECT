from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient


def test_frontend_is_served_without_exposing_project_files(client: TestClient) -> None:
    index = client.get("/")
    assert index.status_code == 200
    assert index.headers["content-type"].startswith("text/html")
    assert "다시, 공간" in index.text
    assert 'id="authLoginButton"' in index.text
    assert 'id="loginForm"' in index.text
    assert 'id="signupForm"' in index.text
    assert 'id="myPageModal"' in index.text
    assert 'id="preferenceForm"' in index.text

    for asset in ("/styles.css", "/app.js"):
        assert client.get(asset).status_code == 200
    assert client.get("/data.js").status_code == 404

    app_script = client.get("/app.js").text
    assert "async function submitLogin" in app_script
    assert "async function submitSignup" in app_script
    assert "async function openMyPage" in app_script
    assert "async function loadSuitability" in app_script

    assert client.get("/backend/main.py").status_code == 404
    assert client.get("/.env").status_code == 404


def test_database_seed_and_space_filter(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "connected"

    response = client.get("/api/v1/spaces", params={"district": "중구", "max_rent": 40})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "database"
    assert body["total"] == 1
    assert body["items"][0]["id"] == "SPC-001"


def test_signup_login_and_me(client: TestClient) -> None:
    email = f"user-{uuid4().hex}@example.com"
    signup_payload = {
        "email": email,
        "password": "safe-password-1234",
        "name": "일반 사용자",
        "phone": "010-1234-5678",
    }

    signup = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup.status_code == 201
    assert signup.json()["email"] == email
    assert signup.json()["role"] == "USER"
    assert "password" not in signup.json()

    duplicate = client.post("/api/v1/auth/signup", json=signup_payload)
    assert duplicate.status_code == 409

    bad_login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert bad_login.status_code == 401

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": signup_payload["password"]}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    forbidden = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert forbidden.status_code == 403


def test_admin_role(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-1234"},
    )
    assert login.status_code == 200

    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["role"] == "ADMIN"


def test_password_change_and_account_deactivation(client: TestClient) -> None:
    email = f"security-{uuid4().hex}@example.com"
    old_password = "old-password-1234"
    new_password = "new-password-5678"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": old_password, "name": "계정 보안 사용자"},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": old_password}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    wrong = client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": new_password},
    )
    assert wrong.status_code == 400
    changed = client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert changed.status_code == 200
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": old_password}
    ).status_code == 401

    relogin = client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_password}
    )
    new_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    deactivated = client.post(
        "/api/v1/users/me/deactivate",
        headers=new_headers,
        json={"password": new_password},
    )
    assert deactivated.status_code == 200
    assert client.get("/api/v1/users/me", headers=new_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_password}
    ).status_code == 403


def test_protected_route_rejects_missing_or_invalid_token(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_mypage_preferences_suitability_and_user_activity(client: TestClient) -> None:
    email = f"mypage-{uuid4().hex}@example.com"
    password = "mypage-password-1234"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "name": "마이페이지 사용자"},
    )
    assert signup.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    empty_preferences = client.get("/api/v1/users/me/preferences", headers=headers)
    assert empty_preferences.status_code == 200
    assert empty_preferences.json()["is_complete"] is False

    no_score = client.get("/api/v1/spaces/SPC-001/suitability", headers=headers)
    assert no_score.status_code == 200
    assert no_score.json()["normalized_score"] is None

    preferences = {
        "preferred_district": "중구",
        "preferred_category": "ART",
        "max_monthly_rent": 40,
        "min_area": 100,
        "parking_required": True,
        "project_summary": "문화예술 전시와 창작 활동을 위한 공간",
    }
    saved = client.put("/api/v1/users/me/preferences", headers=headers, json=preferences)
    assert saved.status_code == 200
    assert saved.json()["is_complete"] is True

    suitability = client.get("/api/v1/spaces/SPC-001/suitability", headers=headers)
    assert suitability.status_code == 200
    assert suitability.json()["normalized_score"] == 100
    assert "활용 용도 적합" in suitability.json()["reasons"]

    recommendation = client.post(
        "/api/v1/recommendations",
        headers=headers,
        json={
            "preferred_district": "중구",
            "purpose_category": "ART",
            "max_monthly_rent": 40,
            "min_area": 100,
            "parking_required": True,
        },
    )
    assert recommendation.status_code == 200
    assert recommendation.json()["results"][0]["space"]["id"] == "SPC-001"
    assert recommendation.json()["results"][0]["normalized_score"] == 100
    assert len(client.get("/api/v1/recommendations/me", headers=headers).json()) == 1

    favorite = client.post("/api/v1/favorites/SPC-001", headers=headers)
    assert favorite.status_code == 201
    favorites = client.get("/api/v1/favorites", headers=headers)
    assert favorites.json()[0]["space"]["id"] == "SPC-001"

    application = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "space_id": "SPC-001",
            "visit_date": "2030-01-15",
            "application_type": "VISIT",
            "applicant_name": "마이페이지 사용자",
            "applicant_phone": "010-1234-5678",
            "message": "공간 내부를 방문해 활용 가능성을 확인하고 싶습니다.",
        },
    )
    assert application.status_code == 201
    application_id = application.json()["id"]
    assert client.get("/api/v1/applications/me", headers=headers).json()[0]["status"] == "PENDING"
    cancelled = client.patch(f"/api/v1/applications/{application_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_admin_application_review_and_application_rules(client: TestClient) -> None:
    email = f"review-{uuid4().hex}@example.com"
    password = "review-password-1234"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "name": "승인 테스트 사용자"},
    )
    user_login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}

    past = client.post(
        "/api/v1/applications",
        headers=user_headers,
        json={
            "space_id": "SPC-001",
            "visit_date": str(date.today() - timedelta(days=1)),
            "applicant_name": "승인 테스트 사용자",
            "applicant_phone": "010-1111-2222",
            "message": "과거 날짜 신청 검증을 위한 메시지입니다.",
        },
    )
    assert past.status_code == 422

    visit_date = date.today() + timedelta(days=30)
    payload = {
        "space_id": "SPC-001",
        "visit_date": str(visit_date),
        "applicant_name": "승인 테스트 사용자",
        "applicant_phone": "010-1111-2222",
        "message": "관리자 승인 흐름을 검증하기 위한 신청입니다.",
    }
    created = client.post("/api/v1/applications", headers=user_headers, json=payload)
    assert created.status_code == 201
    application_id = created.json()["id"]
    assert client.post("/api/v1/applications", headers=user_headers, json=payload).status_code == 409
    assert client.get("/api/v1/admin/applications", headers=user_headers).status_code == 403

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-1234"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    pending = client.get(
        "/api/v1/admin/applications", headers=admin_headers, params={"status": "PENDING"}
    )
    assert pending.status_code == 200
    assert any(item["id"] == application_id for item in pending.json())

    approved = client.patch(
        f"/api/v1/admin/applications/{application_id}/review",
        headers=admin_headers,
        json={"status": "APPROVED", "review_note": "방문 가능 시간을 안내했습니다."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["reviewed_by"] is not None
    assert (
        client.patch(
            f"/api/v1/admin/applications/{application_id}/review",
            headers=admin_headers,
            json={"status": "REJECTED", "review_note": "재처리"},
        ).status_code
        == 409
    )
    mine = client.get("/api/v1/applications/me", headers=user_headers).json()
    assert next(item for item in mine if item["id"] == application_id)["status"] == "APPROVED"


def test_admin_space_crud_and_database_catalog(client: TestClient) -> None:
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-1234"},
    )
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    space_id = f"TEST-{uuid4().hex[:8]}"
    payload = {
        "id": space_id,
        "name": "API 통합 테스트 공간",
        "address": "대구광역시 중구 테스트로 100",
        "district": "중구",
        "category": "OFFICE",
        "category_name": "사무실",
        "area": 50.5,
        "deposit": 100,
        "monthly_rent": 20,
        "maintenance_fee": 3,
        "parking": True,
        "parking_spaces": 2,
        "lat": 35.87,
        "lng": 128.60,
        "description": "공간 목록 API와 관리자 CRUD를 검증하는 공간입니다.",
        "status": "AVAILABLE",
        "utilities": ["인터넷", "화장실"],
        "features": ["테스트 특징"],
        "tags": ["API", "통합테스트"],
        "images": [
            {
                "url": "https://example.com/space.jpg",
                "alt_text": "테스트 공간",
                "sort_order": 0,
            }
        ],
    }
    created = client.post("/api/v1/admin/spaces", headers=headers, json=payload)
    assert created.status_code == 201
    assert created.json()["images"][0]["url"] == "https://example.com/space.jpg"

    listed = client.get("/api/v1/spaces", params={"q": "통합 테스트", "limit": 10})
    assert listed.status_code == 200
    assert any(item["id"] == space_id for item in listed.json()["items"])

    updated = client.patch(
        f"/api/v1/admin/spaces/{space_id}",
        headers=headers,
        json={"monthly_rent": 25, "status": "REMODELING"},
    )
    assert updated.status_code == 200
    assert updated.json()["monthly_rent"] == 25
    assert updated.json()["status"] == "REMODELING"

    deleted = client.delete(f"/api/v1/admin/spaces/{space_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/spaces/{space_id}").status_code == 404
