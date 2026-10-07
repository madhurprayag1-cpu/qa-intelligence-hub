from fastapi.testclient import TestClient


def test_auth_demo_session_endpoint(client: TestClient):
    response = client.post("/auth/demo-session")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "passenger@qahub.io"
    assert data["user"]["role"] == "passenger"


def test_list_capabilities_endpoint(client: TestClient):
    response = client.get("/qa/capabilities?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert data["total"] > 0
    assert len(data["capabilities"]) <= 10
    cap = data["capabilities"][0]
    assert "id" in cap
    assert "domain" in cap
    assert "feature" in cap


def test_get_single_capability_details(client: TestClient):
    # Lookup list to get first ID
    list_resp = client.get("/qa/capabilities?limit=1")
    cap_id = list_resp.json()["capabilities"][0]["id"]

    response = client.get(f"/qa/capabilities/{cap_id}")
    assert response.status_code == 200
    data = response.json()
    assert "capability" in data
    assert data["capability"]["id"] == cap_id
    assert "latest_execution" in data


def test_list_tests_endpoint_with_status_filtering(client: TestClient):
    # ALL tests
    all_resp = client.get("/qa/tests?limit=20")
    assert all_resp.status_code == 200
    all_data = all_resp.json()
    assert "tests" in all_data
    assert all_data["total"] > 0
    assert "passed_count" in all_data

    # PASSED tests only
    passed_resp = client.get("/qa/tests?status=PASSED&limit=20")
    assert passed_resp.status_code == 200
    passed_data = passed_resp.json()
    for t in passed_data["tests"]:
        assert t["status"] == "PASS"

    # Search filter
    search_resp = client.get("/qa/tests?search=airlines&limit=10")
    assert search_resp.status_code == 200
    for t in search_resp.json()["tests"]:
        assert "airline" in t["test_id"].lower() or "airline" in t["test_name"].lower() or "airline" in t["domain"].lower()


def test_get_individual_test_details_and_assertions(client: TestClient):
    tests_resp = client.get("/qa/tests?limit=1")
    test_id = tests_resp.json()["tests"][0]["test_id"]

    resp = client.get(f"/qa/tests/{test_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["test_id"] == test_id
    assert "capability_id" in detail
    assert "assertions" in detail
    assert len(detail["assertions"]) > 0

    # Verify structured Expected vs Actual assertion breakdown
    first_assertion = detail["assertions"][0]
    assert "name" in first_assertion
    assert "expected" in first_assertion
    assert "actual" in first_assertion
    assert "status" in first_assertion

    # Verify sensitive data masking
    assert detail.get("sensitive_data_masked") is True
    assert "password" not in str(detail).lower() or "***" in str(detail) or "no passwords" in str(detail).lower()


def test_list_runs_and_run_detail(client: TestClient):
    # List runs
    runs_resp = client.get("/qa/runs")
    assert runs_resp.status_code == 200
    runs_data = runs_resp.json()
    assert "runs" in runs_data
    assert runs_data["total"] > 0

    first_run = runs_data["runs"][0]
    run_id = first_run["run_id"]
    assert "transaction_id" in first_run
    assert "execution_id" in first_run
    assert "pass_rate" in first_run
    assert "domains" in first_run

    # Drill down into specific run
    detail_resp = client.get(f"/qa/runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["run_id"] == run_id
    assert "domains" in detail
    assert "quality_gate" in detail

    # Domain distribution has all 5 domains + platform
    for dom in ["airline", "healthcare", "fintech", "ecommerce", "telecom"]:
        assert dom in detail["domains"]
        assert "total" in detail["domains"][dom]
        assert "passed" in detail["domains"][dom]

    # Drill down into tests for specific run
    run_tests_resp = client.get(f"/qa/runs/{run_id}/tests?limit=10")
    assert run_tests_resp.status_code == 200
    assert len(run_tests_resp.json()["tests"]) <= 10


def test_negative_cases_and_error_handling(client: TestClient):
    # 1. Non-existent capability ID -> 404
    bad_cap = client.get("/qa/capabilities/NON_EXISTENT_CAP_99999")
    assert bad_cap.status_code == 404
    assert "not found" in bad_cap.json()["detail"].lower()

    # 2. Non-existent test ID -> 404
    bad_test = client.get("/qa/tests/tests/non_existent_file.py::test_missing")
    assert bad_test.status_code == 404
    assert "not found" in bad_test.json()["detail"].lower()

    # 3. Non-existent run ID -> 404
    bad_run = client.get("/qa/runs/RUN-DOES-NOT-EXIST-0000")
    assert bad_run.status_code == 404
    assert "not found" in bad_run.json()["detail"].lower()

    # 4. Unauthenticated booking creation rejected -> 401 Missing Authorization Bearer token
    unauth_booking = client.post(
        "/bookings",
        json={"flight_id": 1, "passenger_name": "Attacker", "passenger_email": "attacker@evil.com", "seats": 1},
    )
    assert unauth_booking.status_code == 401
    assert "Missing Authorization Bearer token" in unauth_booking.json()["detail"]

    # 5. Invalid bearer token format rejected -> 401
    bad_token = client.post(
        "/bookings",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        json={"flight_id": 1, "passenger_name": "Attacker", "passenger_email": "attacker@evil.com", "seats": 1},
    )
    assert bad_token.status_code == 401



def test_serving_revision_verification_endpoint(client: TestClient):
    response = client.get("/qa/release/serving-revision")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "application_version" in data
    assert "environment" in data
    assert "serving_sha" in data
    assert "vercel_environment" in data
    assert "vercel_url" in data
    assert "vercel_region" in data
