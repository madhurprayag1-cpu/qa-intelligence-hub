import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def sqlite_db_override():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)



def test_openapi_schema_endpoint():
    """Verify OpenAPI specification is exposed and adheres to standard schema."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")
    assert "info" in schema
    assert "paths" in schema
    assert "components" in schema


def test_openapi_core_route_coverage():
    """Assert all core platform endpoints are declared in OpenAPI specification."""
    resp = client.get("/openapi.json")
    schema = resp.json()
    paths = schema["paths"]

    expected_routes = [
        "/health",
        "/auth/login",
        "/airlines",
        "/airports",
        "/flights",
        "/search/flights",
        "/bookings",
        "/bookings/ancillaries/catalog",
        "/payments",
        "/defects",
        "/quality-gate/evaluate",
        "/quality-gate/runs",
        "/quality-gate/runs/{run_id}",
        "/ai/rag/query",
        "/ai/rca",
        "/ai/rca/remediate",
        "/ai/security/audit",
    ]

    for route in expected_routes:
        assert route in paths, f"Expected endpoint '{route}' missing from OpenAPI specification"


def test_ancillary_catalog_contract():
    """Verify GET /bookings/ancillaries/catalog strictly matches contract schema."""
    resp = client.get("/bookings/ancillaries/catalog")
    assert resp.status_code == 200
    data = resp.json()

    assert "baggage" in data
    assert "seats" in data
    assert "meals" in data

    # Validate baggage schema
    for tier in data["baggage"]:
        assert "id" in tier
        assert "name" in tier
        assert "price" in tier
        assert isinstance(tier["price"], (int, float))

    # Validate seating schema
    for seat in data["seats"]:
        assert "id" in seat
        assert "name" in seat
        assert "price" in seat

    # Validate meals schema
    for meal in data["meals"]:
        assert "id" in meal
        assert "name" in meal
        assert "price" in meal


def test_defects_catalog_contract():
    """Verify GET /defects returns valid DefectSummary contract models."""
    resp = client.get("/defects")
    assert resp.status_code == 200
    defects = resp.json()

    assert isinstance(defects, list)
    assert len(defects) >= 5

    required_keys = {"id", "name", "category", "affected_endpoint", "description", "how_to_reproduce"}
    for d in defects:
        for k in required_keys:
            assert k in d, f"Missing required contract field '{k}' in defect item {d}"


def test_quality_gate_api_contract_validation():
    """Verify POST /quality-gate/evaluate contract validation and response schema."""
    payload = {
        "policy_name": "PRODUCTION_STRICT",
        "total_tests": 100,
        "passed_tests": 98,
        "failed_tests": 2,
        "critical_defects": 0,
        "contract_failures": 0,
        "security_vulnerabilities": 0,
        "rag_groundedness_score": 0.95,
    }
    resp = client.post("/quality-gate/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "passed" in data
    assert isinstance(data["passed"], bool)
    assert "pass_rate" in data
    assert "status" in data
    assert "violations" in data
    assert isinstance(data["violations"], list)
    assert "signals" in data
    assert "evaluated_at" in data

