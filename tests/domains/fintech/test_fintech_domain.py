"""Comprehensive Automated Tests for FinTech & Digital Banking Domain Pack (Phase 7 Task 7.2).

Adheres strictly to AGENTS.md Sections 1-13, 18-21 and docs/ROADMAP.md Task 7.2:
- Verifies dynamic domain registration & capabilities in domain_registry.
- Validates double-entry bookkeeping ledger models (sum of debits == sum of credits).
- Validates SWIFT ISO 20022 message schemas (pain.001 Credit Transfer Initiation).
- Validates customer KYC verification tiers & AML sanctions screening.
- Validates real-time transaction fraud velocity heuristics and geographic anomaly scoring.
- Validates FinTech SUT REST API endpoints (Accounts, Double-Entry Transfers, SWIFT, KYC, Fraud, FX).
- Verifies intentional synthetic defect injection & detection (DEF-FT-001 through DEF-FT-006).
- Validates domain-scoped RAG knowledge ingestion and isolated vector retrieval.
- Verifies smart regression selector integration and cross-domain isolation with Airline and Healthcare.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.fintech import reset_fintech_store
from domain_registry import DomainCapability, domain_registry
from domains.fintech.defects import FINTECH_DEFECT_REGISTRY, FinTechDefectType
from domains.fintech.domain_pack import fintech_domain_pack
from domains.fintech.factories import (
    AccountFactory,
    FraudAnomalyFactory,
    FXCalculator,
    KYCFactory,
    TransferFactory,
)
from domains.fintech.knowledge import (
    FINTECH_KNOWLEDGE_DOCS,
    get_fintech_knowledge_docs,
)
from domains.fintech.models import (
    BankAccount,
    Currency,
    ISO20022CreditTransfer,
    KYCTier,
    LedgerTransaction,
)
from regression_selector import select_regression_tests


@pytest.fixture(autouse=True)
def clean_fintech_store():
    """Ensures clean in-memory state for every test."""
    reset_fintech_store()
    yield
    reset_fintech_store()


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Domain Pack Registration & Metadata Invariants ---

def test_fintech_domain_pack_registered():
    """Verify FinTech domain pack auto-registers with central registry and adheres to contract."""
    assert domain_registry.is_domain_supported("fintech")
    pack = domain_registry.get("fintech")
    assert pack is not None
    assert pack.domain_id == "fintech"
    assert "Digital Banking" in pack.name
    assert pack.version == "1.0.0"

    # Assert standard QA capabilities
    required_caps = [
        DomainCapability.API_TESTING,
        DomainCapability.DATABASE_TESTING,
        DomainCapability.CONTRACT_TESTING,
        DomainCapability.RAG_AI,
        DomainCapability.AGENTIC_QA,
        DomainCapability.SECURITY_AUDIT,
        DomainCapability.PERFORMANCE_BENCHMARK,
        DomainCapability.QUALITY_GATE,
        DomainCapability.DEFECT_INJECTION,
    ]
    for cap in required_caps:
        assert pack.has_capability(cap), f"Missing capability {cap} in FinTech domain pack"

    # Assert metadata & regulatory standards
    meta = pack.metadata
    assert "ISO 20022" in meta["iso_standard"]
    assert "PCI DSS 4.0" in meta["regulatory_frameworks"]
    assert "USD" in meta["supported_currencies"]
    assert meta["aml_reporting_threshold"] == 10000.0

    # Assert defect catalog
    assert len(pack.defect_catalog) >= 6
    assert "DEF-FT-001" in pack.defect_catalog
    assert "DEF-FT-002" in pack.defect_catalog
    assert "DEF-FT-003" in pack.defect_catalog
    assert "DEF-FT-004" in pack.defect_catalog
    assert "DEF-FT-006" in pack.defect_catalog


# --- 2. Synthetic Test Data Factories ---

def test_account_factory_build_and_batch():
    """Verify AccountFactory generates deterministic, synthetic, and safe account entities."""
    acc = AccountFactory.build(index=0)
    assert acc.account_id.startswith("ACC-")
    assert acc.iban.startswith("GB29QAHB")
    assert len(acc.bic_swift) in [8, 11]
    assert "@qahub-bank.io" in acc.email
    assert acc.balance == 10000.0

    batch = AccountFactory.build_batch(5)
    assert len(batch) == 5
    # Verify uniqueness of account IDs and IBANs
    acc_ids = {a.account_id for a in batch}
    ibans = {a.iban for a in batch}
    assert len(acc_ids) == 5
    assert len(ibans) == 5


def test_double_entry_ledger_invariant():
    """Verify double-entry ledger invariant: sum(debits) must equal sum(credits)."""
    # Balanced transaction must succeed
    balanced = TransferFactory.build_balanced_ledger_txn(
        source_acc_id="ACC-001",
        dest_acc_id="ACC-002",
        amount=750.0,
    )
    assert len(balanced.entries) == 2
    debits = sum(e.amount for e in balanced.entries if e.entry_type == "DEBIT")
    credits = sum(e.amount for e in balanced.entries if e.entry_type == "CREDIT")
    assert debits == credits == 750.0

    # Unbalanced transaction must fail validation
    unbalanced_payload = TransferFactory.build_unbalanced_ledger_txn()
    with pytest.raises(Exception) as exc:
        LedgerTransaction.model_validate(unbalanced_payload)
    assert "invariant violated" in str(exc.value).lower()


def test_iso20022_pain001_transfer_schema():
    """Verify ISO 20022 pain.001 Credit Transfer Initiation schema generation."""
    debtor = AccountFactory.build(index=1, balance=50000.0)
    creditor = AccountFactory.build(index=2, balance=1000.0)

    pain001 = TransferFactory.build_iso20022_pain001(
        debtor_account=debtor,
        creditor_account=creditor,
        amount=12500.0,
    )
    assert pain001.message_id.startswith("MSG-")
    assert pain001.debtor_iban == debtor.iban
    assert pain001.creditor_iban == creditor.iban
    assert pain001.instructed_amount == 12500.0
    assert pain001.purpose_code == "SALA"


def test_kyc_verification_tiers():
    """Verify customer KYC tier assignment and PEP sanctions screening."""
    # Standard applicant with verified income -> Tier 2 ($25,000 limit)
    app1 = KYCFactory.build_applicant(monthly_income=7500.0, index=0)
    assert app1.tax_id_masked.startswith("***-**-")

    # PEP Sanctioned applicant -> flagged
    pep_app = KYCFactory.build_pep_sanctioned_applicant()
    assert "Sanctioned" in pep_app.full_name


def test_fraud_anomaly_heuristics():
    """Verify transaction fraud heuristics factory."""
    clean = FraudAnomalyFactory.build_clean_request()
    assert clean.transactions_in_last_minute == 1

    velocity = FraudAnomalyFactory.build_velocity_spike_request()
    assert velocity.transactions_in_last_minute > 3

    geo = FraudAnomalyFactory.build_geo_impossible_travel_request()
    assert geo.origin_country != geo.destination_country


def test_fx_calculator_precision():
    """Verify currency exchange conversion and penny precision verification."""
    # Standard conversion: 1000 USD to EUR
    res = FXCalculator.convert(
        from_curr=Currency.USD,
        to_curr=Currency.EUR,
        amount=1000.0,
    )
    assert res["fee_amount"] == 5.0  # 0.5% fee
    assert res["precision_verified"] is True
    assert res["drift_detected"] is False

    # Defect conversion: cent truncation
    defect_res = FXCalculator.convert(
        from_curr=Currency.USD,
        to_curr=Currency.EUR,
        amount=1000.0,
        simulate_rounding_defect=True,
    )
    assert defect_res["drift_detected"] is True
    assert defect_res["precision_verified"] is False


# --- 3. FinTech REST API Lifecycle ---

def test_fintech_api_account_lifecycle(client: TestClient):
    """Verify POST and GET /fintech/accounts endpoints."""
    account = AccountFactory.build(index=10)
    payload = account.model_dump()

    # 1. Create Account
    create_resp = client.post("/fintech/accounts", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["account_id"] == account.account_id
    assert created_data["balance"] == account.balance

    # 2. Get Account
    get_resp = client.get(f"/fintech/accounts/{account.account_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["account_id"] == account.account_id

    # 3. Not Found
    missing_resp = client.get("/fintech/accounts/ACC-NON-EXISTENT")
    assert missing_resp.status_code == 404


def test_fintech_api_transfers_double_entry_success(client: TestClient):
    """Verify atomic double-entry fund transfer between two accounts."""
    src = AccountFactory.build(account_holder="Source User", balance=5000.0, index=20)
    dst = AccountFactory.build(account_holder="Dest User", balance=1000.0, index=21)

    client.post("/fintech/accounts", json=src.model_dump())
    client.post("/fintech/accounts", json=dst.model_dump())

    transfer_payload = TransferFactory.build_transfer_payload(
        source_account_id=src.account_id,
        destination_account_id=dst.account_id,
        amount=1200.0,
    )

    resp = client.post("/fintech/transfers", json=transfer_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "SETTLED"
    assert data["source_new_balance"] == 3800.0
    assert data["dest_new_balance"] == 2200.0


def test_fintech_api_transfers_insufficient_funds_rejected(client: TestClient):
    """Verify transfer exceeding available balance is rejected with 409 Conflict."""
    src = AccountFactory.build(balance=200.0, index=30)
    dst = AccountFactory.build(balance=1000.0, index=31)

    client.post("/fintech/accounts", json=src.model_dump())
    client.post("/fintech/accounts", json=dst.model_dump())

    payload = TransferFactory.build_transfer_payload(
        source_account_id=src.account_id,
        destination_account_id=dst.account_id,
        amount=500.0,  # > $200
    )
    resp = client.post("/fintech/transfers", json=payload)
    assert resp.status_code == 409
    assert "Insufficient funds" in resp.json()["detail"]


def test_fintech_api_swift_pain001(client: TestClient):
    """Verify POST /fintech/transfers/swift endpoint."""
    debtor = AccountFactory.build(index=40)
    creditor = AccountFactory.build(index=41)
    pain001 = TransferFactory.build_iso20022_pain001(debtor, creditor, amount=8500.0)

    resp = client.post("/fintech/transfers/swift", json=pain001.model_dump())
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ACCEPTED_SETTLEMENT_IN_PROCESS"
    assert data["iso_standard"] == "pain.001.001.09"


def test_fintech_api_kyc_verification(client: TestClient):
    """Verify POST /fintech/kyc/verify endpoint."""
    applicant = KYCFactory.build_applicant(monthly_income=8000.0)
    resp = client.post("/fintech/kyc/verify", json=applicant.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["assigned_tier"] == KYCTier.TIER_2_VERIFIED.value
    assert data["daily_transfer_limit"] == 25000.0

    # Sanctioned applicant
    pep = KYCFactory.build_pep_sanctioned_applicant()
    pep_resp = client.post("/fintech/kyc/verify", json=pep.model_dump())
    assert pep_resp.status_code == 200
    assert pep_resp.json()["status"] == "REJECTED"


def test_fintech_api_fraud_evaluation(client: TestClient):
    """Verify POST /fintech/fraud/evaluate endpoint."""
    # Clean request
    clean_req = FraudAnomalyFactory.build_clean_request()
    resp1 = client.post("/fintech/fraud/evaluate", json=clean_req.model_dump())
    assert resp1.status_code == 200
    assert resp1.json()["action"] == "ALLOW"

    # Velocity spike request (> 3/min)
    spike_req = FraudAnomalyFactory.build_velocity_spike_request()
    resp2 = client.post("/fintech/fraud/evaluate", json=spike_req.model_dump())
    assert resp2.status_code == 200
    assert resp2.json()["action"] in ["CHALLENGE_2FA", "BLOCK"]
    assert "VELOCITY_SPIKE_EXCEEDED" in resp2.json()["detected_anomalies"]


# --- 4. Intentional Defect Injection & Detection Verification ---

def test_defect_def_ft_001_double_debit_detected(client: TestClient):
    """
    DEF-FT-001 Verification:
    Simulates DOUBLE_DEBIT_RACE defect and confirms balance integrity detection.
    """
    src = AccountFactory.build(balance=1000.0, index=50)
    dst = AccountFactory.build(balance=500.0, index=51)

    client.post("/fintech/accounts", json=src.model_dump())
    client.post("/fintech/accounts", json=dst.model_dump())

    payload = TransferFactory.build_transfer_payload(
        source_account_id=src.account_id,
        destination_account_id=dst.account_id,
        amount=600.0,
    )

    # Injected defect: double debits $1200, driving $1000 balance negative (-$200)
    defect_resp = client.post(
        "/fintech/transfers",
        json=payload,
        headers={"X-Simulate-Defect": FinTechDefectType.DOUBLE_DEBIT_RACE.value},
    )
    assert defect_resp.status_code == 201
    data = defect_resp.json()

    # QA Balance Invariant Assertion: Available balance must never be negative
    assert data["source_new_balance"] < 0, "QA balance check failed: Double debit defect was NOT injected!"
    assert data["source_new_balance"] == -200.0


def test_defect_def_ft_002_precision_rounding_drift_detected(client: TestClient):
    """
    DEF-FT-002 Verification:
    Simulates PRECISION_ROUNDING_DRIFT defect and confirms cent discrepancy detection.
    """
    payload = {
        "from_currency": "USD",
        "to_currency": "EUR",
        "amount": 1000.0,
    }

    # Normal behavior: Preserves exact cents
    normal_resp = client.post("/fintech/exchange/calculate", json=payload)
    assert normal_resp.status_code == 200
    assert normal_resp.json()["precision_verified"] is True
    assert normal_resp.json()["drift_detected"] is False

    # Injected defect: Truncates penny fractions
    defect_resp = client.post(
        "/fintech/exchange/calculate",
        json=payload,
        headers={"X-Simulate-Defect": FinTechDefectType.PRECISION_ROUNDING_DRIFT.value},
    )
    assert defect_resp.status_code == 200
    defect_data = defect_resp.json()

    # QA Precision Assertion: Cent discrepancy detected
    assert defect_data["drift_detected"] is True
    assert defect_data["precision_verified"] is False


def test_defect_def_ft_003_kyc_tier_limit_bypass_detected(client: TestClient):
    """
    DEF-FT-003 Verification:
    Simulates KYC_TIER_LIMIT_BYPASS defect and confirms compliance violation detection.
    """
    src = AccountFactory.build(balance=20000.0, kyc_tier=KYCTier.TIER_1_BASIC, index=60)  # $1,000 limit
    dst = AccountFactory.build(balance=100.0, index=61)

    client.post("/fintech/accounts", json=src.model_dump())
    client.post("/fintech/accounts", json=dst.model_dump())

    payload = TransferFactory.build_transfer_payload(
        source_account_id=src.account_id,
        destination_account_id=dst.account_id,
        amount=5000.0,  # Exceeds $1,000 limit
    )

    # Normal behavior: Must be rejected with 422
    normal_resp = client.post("/fintech/transfers", json=payload)
    assert normal_resp.status_code == 422

    # Injected defect: Permits bypass with 201
    defect_resp = client.post(
        "/fintech/transfers",
        json=payload,
        headers={"X-Simulate-Defect": FinTechDefectType.KYC_TIER_LIMIT_BYPASS.value},
    )
    assert defect_resp.status_code == 201
    # QA Compliance Assertion: Defect allowed transfer exceeding tier limit
    assert defect_resp.json()["amount"] == 5000.0


def test_defect_def_ft_004_fraud_velocity_bypass_detected(client: TestClient):
    """
    DEF-FT-004 Verification:
    Simulates FRAUD_VELOCITY_BYPASS and confirms rate-limiting bypass detection.
    """
    spike_req = FraudAnomalyFactory.build_velocity_spike_request()

    # Injected defect: Returns 'ALLOW' despite 8 txns/minute
    defect_resp = client.post(
        "/fintech/fraud/evaluate",
        json=spike_req.model_dump(),
        headers={"X-Simulate-Defect": FinTechDefectType.FRAUD_VELOCITY_BYPASS.value},
    )
    assert defect_resp.status_code == 200
    # QA Fraud Rule Assertion: High velocity attack was erroneously permitted
    assert defect_resp.json()["action"] == "ALLOW"


def test_defect_def_ft_006_idor_statement_access_detected(client: TestClient):
    """
    DEF-FT-006 Verification:
    Simulates IDOR_ACCOUNT_STATEMENT_ACCESS and confirms security flaw detection.
    """
    account = AccountFactory.build(index=70)
    client.post("/fintech/accounts", json=account.model_dump())

    # Normal behavior: Unauthorized role receives 403 Forbidden
    unauth_resp = client.get(
        f"/fintech/accounts/{account.account_id}",
        headers={"X-User-Role": "unauthorized"},
    )
    assert unauth_resp.status_code == 403

    # Injected defect: Returns 200 OK to unauthorized user
    defect_resp = client.get(
        f"/fintech/accounts/{account.account_id}",
        headers={
            "X-User-Role": "unauthorized",
            "X-Simulate-Defect": FinTechDefectType.IDOR_ACCOUNT_STATEMENT_ACCESS.value,
        },
    )
    # QA Security Assertion: IDOR flaw detected when unauthorized role receives 200 OK
    assert defect_resp.status_code == 200


def test_fintech_defects_catalog_endpoint(client: TestClient):
    """Verify GET /fintech/defects returns all documented FinTech defect scenarios."""
    resp = client.get("/fintech/defects")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 6
    defect_codes = [d["code"] for d in catalog]
    assert "DEF-FT-001" in defect_codes
    assert "DEF-FT-002" in defect_codes
    assert "DEF-FT-003" in defect_codes
    assert "DEF-FT-004" in defect_codes


# --- 5. Domain RAG Knowledge Base & Cross-Domain Isolation ---

def test_fintech_knowledge_docs_provider():
    """Verify synthetic FinTech knowledge provider conforms to contract."""
    docs = get_fintech_knowledge_docs()
    assert len(docs) == 5

    doc_ids = [d["document_id"] for d in docs]
    assert "FINTECH-LEDGER-01" in doc_ids
    assert "FINTECH-ISO20022-01" in doc_ids
    assert "FINTECH-KYC-AML-01" in doc_ids
    assert "FINTECH-FRAUD-01" in doc_ids
    assert "FINTECH-PCIDSS-01" in doc_ids

    for doc in docs:
        assert doc["metadata"]["domain"] == "fintech"
        assert len(doc["text"]) > 50


@pytest.mark.anyio
async def test_fintech_rag_isolated_query():
    """Verify domain-scoped RAG query returns only FinTech evidence."""
    from rag import RAGPipeline
    from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider

    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
    )
    # Ingest FinTech domain knowledge
    loaded_count = pipeline.load_domain_knowledge(fintech_domain_pack)
    assert loaded_count == 5

    # Query with domain="fintech"
    res = await pipeline.query("What are the double-entry bookkeeping rules?", domain="fintech")
    assert res.refusal is False
    assert len(res.retrieved_chunks) > 0
    for chunk in res.retrieved_chunks:
        assert chunk.metadata.get("domain") == "fintech"


# --- 6. Smart Regression Selector Integration & Cross-Domain Isolation ---

def test_fintech_smart_regression_selector():
    """Verify changes to FinTech domain files trigger FinTech regression tests."""
    plan = select_regression_tests(["domains/fintech/factories.py", "domains/fintech/models.py"])
    assert "tests/domains/fintech/test_fintech_domain.py" in plan.selected_test_files
    assert any("fintech" in tag for tag in plan.selected_tags)


def test_cross_domain_isolation_airline_and_healthcare():
    """Verify Airline and Healthcare regression mappings remain fully intact without FinTech leakage."""
    airline_plan = select_regression_tests(["backend/app/routers/payments.py"])
    assert "tests/api/test_payments.py" in airline_plan.selected_test_files
    assert "payment" in airline_plan.selected_tags

    healthcare_plan = select_regression_tests(["domains/healthcare/factories.py"])
    assert "tests/domains/healthcare/test_healthcare_domain.py" in healthcare_plan.selected_test_files
    assert any("healthcare" in tag for tag in healthcare_plan.selected_tags)
