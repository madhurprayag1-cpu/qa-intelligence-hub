"""Deterministic Test Suite for Task 7.3: Dynamic Domain Runtime Switching via QA_DOMAIN.

Adheres strictly to AGENTS.md Sections 1-4, 5, 8, 10, 11, 18, and 37:
1. Default domain behavior (preserves 'airline' fallback when QA_DOMAIN is unset)
2. Airline selection (QA_DOMAIN='airline' resolves airline domain pack & factories)
3. Healthcare selection (QA_DOMAIN='healthcare' resolves healthcare domain pack & factories)
4. FinTech selection (QA_DOMAIN='fintech' resolves fintech domain pack & factories)
5. Invalid domain handling (UnsupportedDomainError and HTTP 400 with actionable error)
6. Runtime/domain isolation (zero cross-domain leakage across factories, defects, RAG sources)
7. Regression-selector behavior (attaches active_domain and supports domain scoping)
8. RAG/domain scoping (RAG queries and knowledge ingestion partition by active domain)
9. API domain lifecycle (GET /qa/domain, POST /qa/domain/switch, POST /qa/domain/reset)
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider
from domain_registry import DomainCapability, UnsupportedDomainError, domain_registry
from factories import get_domain_factories
from rag import RAGPipeline
from regression_selector import select_regression_tests


@pytest.fixture(autouse=True)
def reset_domain_state(monkeypatch):
    """Ensures each test starts and ends with clean domain registry state."""
    domain_registry.reset_active_domain()
    monkeypatch.delenv("QA_DOMAIN", raising=False)
    yield
    domain_registry.reset_active_domain()
    monkeypatch.delenv("QA_DOMAIN", raising=False)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Default Domain Behavior
# ---------------------------------------------------------------------------

def test_default_domain_behavior(monkeypatch):
    """Verify that when QA_DOMAIN is unset, the platform seamlessly defaults to 'airline'."""
    monkeypatch.delenv("QA_DOMAIN", raising=False)
    domain_registry.reset_active_domain()

    assert domain_registry.get_active_domain_id() == "airline"
    active_pack = domain_registry.get_active_domain()
    assert active_pack is not None
    assert active_pack.domain_id == "airline"
    assert "Airline" in active_pack.name

    summary = domain_registry.get_domain_summary()
    assert summary["active_domain"] == "airline"
    assert summary["default_domain"] == "airline"
    assert "airline" in summary["registered_domains"]
    assert "healthcare" in summary["registered_domains"]
    assert "fintech" in summary["registered_domains"]
    assert "ecommerce" in summary["registered_domains"]
    assert "telecom" in summary["registered_domains"]
    assert summary["runtime_override_active"] is False

    # Default factories resolve airline factories
    factories = get_domain_factories()
    assert "PassengerFactory" in factories
    assert "BookingPayloadFactory" in factories
    passenger = factories["PassengerFactory"].build(index=0)
    assert passenger.name != ""
    assert "@qahub.io" in passenger.email


# ---------------------------------------------------------------------------
# 2. Airline Selection
# ---------------------------------------------------------------------------

def test_airline_selection_via_env(monkeypatch):
    """Verify explicit selection of 'airline' domain via QA_DOMAIN."""
    monkeypatch.setenv("QA_DOMAIN", "airline")

    assert domain_registry.get_active_domain_id() == "airline"
    pack = domain_registry.get_active_domain()
    assert pack.domain_id == "airline"
    assert pack.has_capability(DomainCapability.UI_AUTOMATION)
    assert "DEF-001" in pack.defect_catalog

    factories = domain_registry.get_active_factories()
    assert "PassengerFactory" in factories
    assert "PaymentPayloadFactory" in factories
    p = factories["PassengerFactory"].build(index=1)
    assert p.name != ""


# ---------------------------------------------------------------------------
# 3. Healthcare Selection
# ---------------------------------------------------------------------------

def test_healthcare_selection_via_env(monkeypatch):
    """Verify explicit selection of 'healthcare' domain via QA_DOMAIN."""
    monkeypatch.setenv("QA_DOMAIN", "healthcare")

    assert domain_registry.get_active_domain_id() == "healthcare"
    pack = domain_registry.get_active_domain()
    assert pack.domain_id == "healthcare"
    assert "HL7 FHIR" in pack.name
    assert "DEF-HC-001" in pack.defect_catalog

    factories = domain_registry.get_active_factories()
    assert "PatientFactory" in factories
    assert "ClinicalDosageCalculator" in factories
    patient = factories["PatientFactory"].build(index=0)
    assert patient.mrn.startswith("MRN-")
    assert patient.full_name != ""
    assert patient.gender in ["male", "female"]

    # Verify clinical calculator factory utility
    dosage = factories["ClinicalDosageCalculator"].calculate(weight_kg=15.0, mg_per_kg=20.0)
    assert dosage["single_dose_mg"] == 300.0
    assert dosage["precision_verified"] is True


# ---------------------------------------------------------------------------
# 4. FinTech Selection
# ---------------------------------------------------------------------------

def test_fintech_selection_via_env(monkeypatch):
    """Verify explicit selection of 'fintech' domain via QA_DOMAIN."""
    monkeypatch.setenv("QA_DOMAIN", "fintech")

    assert domain_registry.get_active_domain_id() == "fintech"
    pack = domain_registry.get_active_domain()
    assert pack.domain_id == "fintech"
    assert "Digital Banking" in pack.name
    assert "DEF-FT-001" in pack.defect_catalog

    factories = domain_registry.get_active_factories()
    assert "AccountFactory" in factories
    assert "FXCalculator" in factories
    account = factories["AccountFactory"].build(index=0)
    assert account.account_id.startswith("ACC-")
    assert account.balance >= 0.0

    # Verify FX calculator utility
    from domains.fintech.models import Currency
    converted = factories["FXCalculator"].convert(
        amount=100.0, from_curr=Currency.USD, to_curr=Currency.EUR
    )
    assert converted["converted_amount"] > 0.0


# ---------------------------------------------------------------------------
# 4b. E-Commerce Selection
# ---------------------------------------------------------------------------

def test_ecommerce_selection_via_env(monkeypatch):
    """Verify explicit selection of 'ecommerce' domain via QA_DOMAIN."""
    monkeypatch.setenv("QA_DOMAIN", "ecommerce")

    assert domain_registry.get_active_domain_id() == "ecommerce"
    pack = domain_registry.get_active_domain()
    assert pack.domain_id == "ecommerce"
    assert "Digital Retail" in pack.name
    assert "DEF-EC-001" in pack.defect_catalog

    factories = domain_registry.get_active_factories()
    assert "ProductFactory" in factories
    assert "OrderFactory" in factories
    assert "PricingCalculator" in factories
    product = factories["ProductFactory"].build(index=0)
    assert product.sku.startswith("SKU-")
    assert product.price > 0.0


# ---------------------------------------------------------------------------
# 4c. Telecom Selection
# ---------------------------------------------------------------------------

def test_telecom_selection_via_env(monkeypatch):
    """Verify explicit selection of 'telecom' domain via QA_DOMAIN."""
    monkeypatch.setenv("QA_DOMAIN", "telecom")

    assert domain_registry.get_active_domain_id() == "telecom"
    pack = domain_registry.get_active_domain()
    assert pack.domain_id == "telecom"
    assert "Telecom" in pack.name
    assert "DEF-TC-001" in pack.defect_catalog

    factories = domain_registry.get_active_factories()
    assert "SubscriberFactory" in factories
    assert "CDRFactory" in factories
    sub = factories["SubscriberFactory"].build(index=0)
    assert sub.msisdn.startswith("+1")
    assert sub.sim.iccid.startswith("89310")


# ---------------------------------------------------------------------------
# 5. Invalid Domain Handling
# ---------------------------------------------------------------------------

def test_invalid_domain_handling(monkeypatch, client):
    """Verify that unrecognized domains fail explicitly and safely."""
    # 1. validate_domain raises UnsupportedDomainError
    with pytest.raises(UnsupportedDomainError) as exc_info:
        domain_registry.validate_domain("telecom_quantum_crypto")
    assert "telecom_quantum_crypto" in str(exc_info.value)
    assert "Supported domains" in str(exc_info.value)

    # 2. Empty or invalid type string validation
    with pytest.raises(UnsupportedDomainError):
        domain_registry.validate_domain("")

    # 3. set_active_domain raises UnsupportedDomainError on invalid domain
    with pytest.raises(UnsupportedDomainError):
        domain_registry.set_active_domain("invalid_domain")

    # 4. Strict mode get_active_domain_id raises UnsupportedDomainError
    monkeypatch.setenv("QA_DOMAIN", "invalid_domain")
    with pytest.raises(UnsupportedDomainError):
        domain_registry.get_active_domain_id(strict=True)

    # 5. Non-strict mode gracefully falls back to default domain
    assert domain_registry.get_active_domain_id(strict=False) == "airline"

    # 6. API POST /qa/domain/switch returns HTTP 400 for unknown domain
    res = client.post("/qa/domain/switch", json={"domain": "unsupported_xyz"})
    assert res.status_code == 400
    err = res.json()
    assert "unsupported_xyz" in err["detail"]

    # 7. API POST /ai/rag/query returns HTTP 400 for unknown domain
    rag_res = client.post(
        "/ai/rag/query",
        json={"question": "What is the policy?", "domain": "unknown_industry"},
    )
    assert rag_res.status_code == 400
    assert "unknown_industry" in rag_res.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Runtime / Domain Isolation
# ---------------------------------------------------------------------------

def test_runtime_domain_isolation(monkeypatch):
    """Verify complete isolation between domain packs: zero cross-domain leakage."""
    # Test Healthcare isolation
    monkeypatch.setenv("QA_DOMAIN", "healthcare")
    hlth_factories = domain_registry.get_active_factories()
    assert "PatientFactory" in hlth_factories
    assert "PassengerFactory" not in hlth_factories
    assert "AccountFactory" not in hlth_factories

    hlth_pack = domain_registry.get_active_domain()
    assert all("HC" in code for code in hlth_pack.defect_catalog.keys())
    assert all("HEALTHCARE" in src for src in hlth_pack.rag_sources)

    # Test FinTech isolation
    monkeypatch.setenv("QA_DOMAIN", "fintech")
    fin_factories = domain_registry.get_active_factories()
    assert "AccountFactory" in fin_factories
    assert "PatientFactory" not in fin_factories
    assert "PassengerFactory" not in fin_factories

    fin_pack = domain_registry.get_active_domain()
    assert all("FT" in code for code in fin_pack.defect_catalog.keys())
    assert all("FINTECH" in src for src in fin_pack.rag_sources)

    # Test Airline isolation
    monkeypatch.setenv("QA_DOMAIN", "airline")
    air_factories = domain_registry.get_active_factories()
    assert "PassengerFactory" in air_factories
    assert "PatientFactory" not in air_factories
    assert "AccountFactory" not in air_factories
    assert "ProductFactory" not in air_factories
    assert "SubscriberFactory" not in air_factories

    air_pack = domain_registry.get_active_domain()
    assert all("DEF-" in code and "HC" not in code and "FT" not in code and "EC" not in code and "TC" not in code for code in air_pack.defect_catalog.keys())
    assert all("AIRLINE" in src for src in air_pack.rag_sources)

    # Test E-Commerce isolation
    monkeypatch.setenv("QA_DOMAIN", "ecommerce")
    ec_factories = domain_registry.get_active_factories()
    assert "ProductFactory" in ec_factories
    assert "CartFactory" in ec_factories
    assert "PassengerFactory" not in ec_factories
    assert "SubscriberFactory" not in ec_factories

    ec_pack = domain_registry.get_active_domain()
    assert all("EC" in code for code in ec_pack.defect_catalog.keys())
    assert all("ECOMMERCE" in src for src in ec_pack.rag_sources)

    # Test Telecom isolation
    monkeypatch.setenv("QA_DOMAIN", "telecom")
    tc_factories = domain_registry.get_active_factories()
    assert "SubscriberFactory" in tc_factories
    assert "CDRFactory" in tc_factories
    assert "ProductFactory" not in tc_factories
    assert "PatientFactory" not in tc_factories

    tc_pack = domain_registry.get_active_domain()
    assert all("TC" in code for code in tc_pack.defect_catalog.keys())
    assert all("TELECOM" in src for src in tc_pack.rag_sources)


# ---------------------------------------------------------------------------
# 7. Regression Selector Behavior
# ---------------------------------------------------------------------------

def test_regression_selector_domain_behavior(monkeypatch):
    """Verify regression selector records active_domain and supports domain scoping."""
    # 1. Active domain is airline
    monkeypatch.setenv("QA_DOMAIN", "airline")
    plan_air = select_regression_tests(["domains/airline/models.py"])
    assert plan_air.active_domain == "airline"
    assert any("flight" in t or "booking" in t or "airline" in t for t in plan_air.selected_test_files)

    # 2. Active domain is healthcare
    monkeypatch.setenv("QA_DOMAIN", "healthcare")
    plan_hlth = select_regression_tests(["domains/healthcare/dosages.py"])
    assert plan_hlth.active_domain == "healthcare"
    assert "tests/domains/healthcare/test_healthcare_domain.py" in plan_hlth.selected_test_files

    # 3. Active domain is fintech
    monkeypatch.setenv("QA_DOMAIN", "fintech")
    plan_fin = select_regression_tests(["domains/fintech/transfers.py"])
    assert plan_fin.active_domain == "fintech"
    assert "tests/domains/fintech/test_fintech_domain.py" in plan_fin.selected_test_files

    # 4. Active domain is ecommerce
    monkeypatch.setenv("QA_DOMAIN", "ecommerce")
    plan_ec = select_regression_tests(["domains/ecommerce/catalog.py"])
    assert plan_ec.active_domain == "ecommerce"
    assert "tests/domains/ecommerce/test_ecommerce_domain.py" in plan_ec.selected_test_files

    # 5. Active domain is telecom
    monkeypatch.setenv("QA_DOMAIN", "telecom")
    plan_tc = select_regression_tests(["domains/telecom/subscribers.py"])
    assert plan_tc.active_domain == "telecom"
    assert "tests/domains/telecom/test_telecom_domain.py" in plan_tc.selected_test_files

    # 6. Domain scoping isolation: when scoped to fintech, healthcare files fallback to default
    scoped_plan = select_regression_tests(
        ["domains/healthcare/dosages.py"],
        domain_id="fintech",
        scope_to_domain=True,
    )
    assert scoped_plan.active_domain == "fintech"
    # Healthcare patterns not present in fintech scoped map, so it hits default API fallback
    assert "tests/api/" in scoped_plan.selected_test_files


# ---------------------------------------------------------------------------
# 8. RAG / Domain Scoping
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_rag_domain_scoping(monkeypatch):
    """Verify RAG query respects active domain partition and refuses cross-domain queries."""
    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
    )

    # Ingest distinct domain docs for all 5 domains
    pipeline.ingest_document(
        document_id="AIR-TEST-01",
        text="Airlines enforce IATA NDC 21.3 for distribution of ancillaries and flight seats.",
        domain="airline",
    )
    pipeline.ingest_document(
        document_id="HLTH-TEST-01",
        text="Healthcare clinics enforce HIPAA Safe Harbor and HL7 FHIR for pediatric records.",
        domain="healthcare",
    )
    pipeline.ingest_document(
        document_id="FIN-TEST-01",
        text="FinTech ledgers mandate double-entry bookkeeping and ISO 20022 payment messages.",
        domain="fintech",
    )
    pipeline.ingest_document(
        document_id="EC-TEST-01",
        text="E-Commerce digital stores enforce 30-day return policy and automated RMA restocking.",
        domain="ecommerce",
    )
    pipeline.ingest_document(
        document_id="TC-TEST-01",
        text="Telecom 5G networks enforce Fair Usage Policy with 50GB high-speed quota and throttling.",
        domain="telecom",
    )

    # 1. Query scoped to 'healthcare'
    res_hlth = await pipeline.query("FHIR standards", domain="healthcare")
    assert not res_hlth.refusal
    assert any("HLTH-TEST-01" in c.document_id for c in res_hlth.retrieved_chunks)

    # 2. Query scoped to 'ecommerce'
    res_ec = await pipeline.query("RMA return policy", domain="ecommerce")
    assert not res_ec.refusal
    assert any("EC-TEST-01" in c.document_id for c in res_ec.retrieved_chunks)

    # 3. Query scoped to 'telecom'
    res_tc = await pipeline.query("5G Fair Usage Policy", domain="telecom")
    assert not res_tc.refusal
    assert any("TC-TEST-01" in c.document_id for c in res_tc.retrieved_chunks)

    # 4. Cross-domain refusal: querying telecom concepts under domain='ecommerce' triggers refusal
    res_cross = await pipeline.query("5G mobile throttling", domain="ecommerce")
    assert res_cross.refusal is True
    assert "No relevant domain knowledge" in res_cross.answer
    assert res_cross.domain == "ecommerce"

    # 5. Explicit domain=None searches across all 5 partitions
    all_chunks = pipeline.retrieve("policy standards", domain=None)
    domains_found = {c.metadata.get("domain") for c, _ in all_chunks}
    assert "airline" in domains_found
    assert "healthcare" in domains_found
    assert "fintech" in domains_found
    assert "ecommerce" in domains_found
    assert "telecom" in domains_found


# ---------------------------------------------------------------------------
# 9. API Domain Lifecycle (GET, POST switch, POST reset)
# ---------------------------------------------------------------------------

def test_api_domain_switch_and_reset_lifecycle(client):
    """Verify full HTTP API lifecycle across all five production domain packs."""
    # 1. Initial status: airline
    res = client.get("/qa/domain")
    assert res.status_code == 200
    data = res.json()
    assert data["active_domain"] == "airline"
    assert data["runtime_override_active"] is False
    assert len(data["registered_domains"]) >= 5

    # 2. Switch to healthcare
    switch_res = client.post("/qa/domain/switch", json={"domain": "healthcare"})
    assert switch_res.status_code == 200
    assert switch_res.json()["active_domain"] == "healthcare"

    # 3. Switch to fintech
    switch_res2 = client.post("/qa/domain/switch", json={"domain": "fintech"})
    assert switch_res2.status_code == 200
    assert switch_res2.json()["active_domain"] == "fintech"

    # 4. Switch to ecommerce
    switch_res3 = client.post("/qa/domain/switch", json={"domain": "ecommerce"})
    assert switch_res3.status_code == 200
    assert switch_res3.json()["active_domain"] == "ecommerce"

    # 5. Switch to telecom
    switch_res4 = client.post("/qa/domain/switch", json={"domain": "telecom"})
    assert switch_res4.status_code == 200
    assert switch_res4.json()["active_domain"] == "telecom"

    status_res = client.get("/qa/domain")
    assert status_res.status_code == 200
    assert status_res.json()["active_domain"] == "telecom"
    assert status_res.json()["runtime_override_active"] is True

    # 6. Reset back to default
    reset_res = client.post("/qa/domain/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "RESET"
    assert reset_data["active_domain"] == "airline"

    # 7. Confirm GET reflects reset state
    final_res = client.get("/qa/domain")
    assert final_res.json()["active_domain"] == "airline"
    assert final_res.json()["runtime_override_active"] is False
