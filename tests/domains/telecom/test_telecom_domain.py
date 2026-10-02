"""Automated Test Suite for Telecom / 5G Mobile & BSS/OSS Domain Pack.

Adheres strictly to AGENTS.md Sections 8, 9, 11, 12, 13, 17, 37:
- Deterministic unit, integration, and synthetic defect verification for Telecom domain.
- Covers data models, state transitions, rating engine calculations, and REST API endpoints.
- Verifies detection of all 6 intentional telecom defects (DEF-TC-001 through DEF-TC-006).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.telecom import reset_telecom_store
from domain_registry import DomainCapability, domain_registry
from domains.telecom.defects import TELECOM_DEFECT_REGISTRY, TelecomDefectType
from domains.telecom.factories import (
    CDRFactory,
    PlanFactory,
    SIMFactory,
    SubscriberFactory,
    get_telecom_factories,
)
from domains.telecom.knowledge import TELECOM_KNOWLEDGE_DOCS, get_telecom_rag_docs
from domains.telecom.models import (
    CallDetailRecord,
    CallType,
    DataPlan,
    InvalidSubscriptionStateTransitionError,
    PlanType,
    RatingEngine,
    RatingZone,
    SIMCard,
    Subscriber,
    SubscriptionStateMachine,
    SubscriptionStatus,
)


@pytest.fixture(autouse=True)
def clean_telecom_store():
    reset_telecom_store()
    yield
    reset_telecom_store()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Model & Validation Tests
# ---------------------------------------------------------------------------

def test_sim_card_and_msisdn_validation():
    """Verify SIMCard and MSISDN format validations."""
    sim = SIMCard(
        iccid="8931041012345678901",
        imsi="310260123456789",
        is_esim=False,
    )
    assert sim.iccid.startswith("89310")
    assert len(sim.imsi) == 15

    # Invalid ICCID (too short)
    with pytest.raises(ValueError):
        SIMCard(iccid="12345", imsi="310260123456789")

    # Invalid IMSI (not 15 digits)
    with pytest.raises(ValueError):
        SIMCard(iccid="8931041012345678901", imsi="12345")


def test_rating_engine_voice_and_data_calculations():
    """Verify accurate calculation of voice overage, data overage, and roaming rates."""
    plan = DataPlan(
        plan_id="TEST-PLAN",
        name="Test Plan",
        plan_type=PlanType.POSTPAID,
        monthly_fee=30.0,
        voice_minutes_included=100,
        sms_included=100,
        data_gb_included=5.0,  # 5120 MB
        overage_voice_per_min=0.10,
        overage_data_per_mb=0.02,
    )
    subscriber = Subscriber(
        subscriber_id="SUB-TEST-01",
        msisdn="+14155550100",
        sim=SIMFactory.build(0),
        plan=plan,
        minutes_used=90,
        data_used_mb=5000.0,  # 120 MB remaining in quota
    )

    # Within included voice quota: 10 minutes used (90 + 10 = 100 <= 100) -> 0.0
    voice_cdr = CDRFactory.build_voice_cdr(0, duration_seconds=600)  # 10 mins
    charge = RatingEngine.rate_cdr(subscriber, voice_cdr)
    assert charge == 0.0

    # Exceeding voice quota: 25 minutes used -> 10 minutes in quota, 15 minutes overage @ $0.10 -> $1.50
    voice_cdr_over = CDRFactory.build_voice_cdr(1, duration_seconds=1500)  # 25 mins
    charge_over = RatingEngine.rate_cdr(subscriber, voice_cdr_over)
    assert charge_over == 1.50

    # Data within quota: 100 MB used <= 120 MB remaining -> 0.0
    data_cdr = CDRFactory.build_data_cdr(0, mb_transferred=100.0)
    data_charge = RatingEngine.rate_cdr(subscriber, data_cdr)
    assert data_charge == 0.0

    # Data overage: 220 MB used -> 120 MB in quota, 100 MB overage @ $0.02 -> $2.00
    data_cdr_over = CDRFactory.build_data_cdr(1, mb_transferred=220.0)
    data_charge_over = RatingEngine.rate_cdr(subscriber, data_cdr_over)
    assert data_charge_over == 2.00


def test_subscription_state_machine_transitions():
    """Verify valid transitions and rejection of illegal state changes."""
    sub = SubscriberFactory.build(0, status=SubscriptionStatus.PENDING_ACTIVATION)

    # Valid: PENDING_ACTIVATION -> ACTIVE
    SubscriptionStateMachine.transition(sub, SubscriptionStatus.ACTIVE)
    assert sub.status == SubscriptionStatus.ACTIVE

    # Valid: ACTIVE -> SUSPENDED
    SubscriptionStateMachine.transition(sub, SubscriptionStatus.SUSPENDED)
    assert sub.status == SubscriptionStatus.SUSPENDED

    # Valid: SUSPENDED -> ACTIVE
    SubscriptionStateMachine.transition(sub, SubscriptionStatus.ACTIVE)
    assert sub.status == SubscriptionStatus.ACTIVE

    # Valid: ACTIVE -> CANCELLED
    SubscriptionStateMachine.transition(sub, SubscriptionStatus.CANCELLED)
    assert sub.status == SubscriptionStatus.CANCELLED

    # Invalid: CANCELLED -> ACTIVE (must raise InvalidSubscriptionStateTransitionError)
    with pytest.raises(InvalidSubscriptionStateTransitionError):
        SubscriptionStateMachine.transition(sub, SubscriptionStatus.ACTIVE)


def test_telecom_factories_deterministic_generation():
    """Verify deterministic generation of subscribers, plans, SIMs, and CDRs."""
    s1 = SubscriberFactory.build(1)
    s2 = SubscriberFactory.build(1)
    s3 = SubscriberFactory.build(2)

    assert s1.msisdn == s2.msisdn
    assert s1.sim.iccid == s2.sim.iccid
    assert s1.msisdn != s3.msisdn

    plan = PlanFactory.build(0)
    assert plan.plan_id.startswith("PLAN-")

    cdr = CDRFactory.build_voice_cdr(10, duration_seconds=120)
    assert cdr.cdr_id == "CDR-V-0000010"
    assert cdr.duration_seconds == 120


def test_api_list_plans_and_provision_subscriber(client):
    """Verify REST API plan listing and subscriber provisioning."""
    plans_res = client.get("/telecom/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()
    assert len(plans) >= 3

    sub = SubscriberFactory.build(10, status=SubscriptionStatus.ACTIVE)
    create_res = client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["msisdn"] == sub.msisdn


# ---------------------------------------------------------------------------
# 2. Defect Detection Tests (DEF-TC-001 through DEF-TC-006)
# ---------------------------------------------------------------------------

def test_defect_def_tc_001_sim_swap_race_detected(client):
    """DEF-TC-001: Race condition leaves twin active SIMs during swap."""
    sub = SubscriberFactory.build(20, status=SubscriptionStatus.ACTIVE)
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    # Normal mode: clean swap
    swap_res = client.post(
        f"/telecom/subscribers/{sub.msisdn}/sim-swap",
        json={"new_iccid": "8931099999999999999", "new_imsi": "310260999999999"},
    )
    assert swap_res.status_code == 200
    assert swap_res.json()["twin_sim_active"] is False

    # Defect mode: race causes twin active SIMs
    defect_swap = client.post(
        f"/telecom/subscribers/{sub.msisdn}/sim-swap",
        json={"new_iccid": "8931088888888888888", "new_imsi": "310260888888888"},
        headers={"X-Simulate-Defect": TelecomDefectType.SIM_SWAP_RACE.value},
    )
    assert defect_swap.status_code == 200
    swap_data = defect_swap.json()
    assert swap_data["twin_sim_active"] is True
    assert len(swap_data["active_iccids"]) == 2


def test_defect_def_tc_002_cdr_overage_miscalculation_detected(client):
    """DEF-TC-002: Fractional MB rounded up to whole GBs inflating charges."""
    sub = SubscriberFactory.build(30, plan_id="PLAN-PREPAID-STARTER", status=SubscriptionStatus.ACTIVE, balance=100.0)
    # Deplete data allowance
    sub.data_used_mb = sub.plan.data_gb_included * 1024.0
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    # Usage: 50 MB transferred
    cdr = CDRFactory.build_data_cdr(101, msisdn=sub.msisdn, mb_transferred=50.0)

    # Defect mode: overbills by rounding 50 MB to 1 full GB (1024 MB * 0.02 = $20.48)
    defect_rate = client.post(
        "/telecom/cdr/rate",
        json={"cdr": cdr.model_dump(mode="json")},
        headers={"X-Simulate-Defect": TelecomDefectType.CDR_OVERAGE_MISCALCULATION.value},
    )
    assert defect_rate.status_code == 200
    defect_data = defect_rate.json()
    # Normal 50 MB overage @ $0.02 is $1.00; defect charge is >= $20.00
    assert defect_data["rated_amount"] >= 20.0


def test_defect_def_tc_003_unauthorized_roaming_leak_detected(client):
    """DEF-TC-003: Processes roaming CDR for non-roaming subscriber."""
    sub = SubscriberFactory.build(40, roaming_allowed=False, balance=50.0)
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    roaming_cdr = CDRFactory.build_voice_cdr(
        201, msisdn=sub.msisdn, zone=RatingZone.ROAMING_ZONE_1, duration_seconds=120
    )

    # Normal mode: rejects with 403 Forbidden
    normal_res = client.post("/telecom/cdr/rate", json={"cdr": roaming_cdr.model_dump(mode="json")})
    assert normal_res.status_code == 403
    assert "TEL-ERR-ROAMING-NOT-ALLOWED" in normal_res.json()["detail"]

    # Defect mode: improperly allows roaming CDR
    defect_res = client.post(
        "/telecom/cdr/rate",
        json={"cdr": roaming_cdr.model_dump(mode="json")},
        headers={"X-Simulate-Defect": TelecomDefectType.UNAUTHORIZED_ROAMING_LEAK.value},
    )
    assert defect_res.status_code == 200
    assert defect_res.json()["status"] == "RATED_AND_BILLED"


def test_defect_def_tc_004_double_billing_cdr_race_detected(client):
    """DEF-TC-004: Duplicate CDR submission allowed without deduplication."""
    sub = SubscriberFactory.build(50, balance=100.0)
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    cdr = CDRFactory.build_voice_cdr(301, msisdn=sub.msisdn, duration_seconds=180)

    # First submission succeeds
    res1 = client.post("/telecom/cdr/rate", json={"cdr": cdr.model_dump(mode="json")})
    assert res1.status_code == 200

    # Normal mode second submission: blocked with 409 Conflict
    res2 = client.post("/telecom/cdr/rate", json={"cdr": cdr.model_dump(mode="json")})
    assert res2.status_code == 409
    assert "DUPLICATE_USAGE" in res2.json()["detail"]

    # Defect mode: bypasses deduplication, billing again
    res_defect = client.post(
        "/telecom/cdr/rate",
        json={"cdr": cdr.model_dump(mode="json")},
        headers={"X-Simulate-Defect": TelecomDefectType.DOUBLE_BILLING_CDR_RACE.value},
    )
    assert res_defect.status_code == 200
    assert res_defect.json()["status"] == "RATED_AND_BILLED"


def test_defect_def_tc_005_invalid_state_transition_detected(client):
    """DEF-TC-005: State machine bypass permits illegal activation."""
    sub = SubscriberFactory.build(60, status=SubscriptionStatus.CANCELLED)
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    # Normal mode: CANCELLED -> ACTIVE is rejected with 422
    normal_res = client.post(
        f"/telecom/subscribers/{sub.msisdn}/status",
        json={"target_status": SubscriptionStatus.ACTIVE.value},
    )
    assert normal_res.status_code == 422

    # Defect mode: force status bypasses FSM rules
    defect_res = client.post(
        f"/telecom/subscribers/{sub.msisdn}/status",
        json={"target_status": SubscriptionStatus.ACTIVE.value},
        headers={"X-Simulate-Defect": TelecomDefectType.INVALID_STATE_TRANSITION.value},
    )
    assert defect_res.status_code == 200
    assert defect_res.json()["status"] == SubscriptionStatus.ACTIVE.value


def test_defect_def_tc_006_cdr_pii_unmasked_log_detected(client):
    """DEF-TC-006: Diagnostic response exposes unmasked CPNI PII."""
    sub = SubscriberFactory.build(70)
    client.post("/telecom/subscribers", json=sub.model_dump(mode="json"))

    # Normal mode: PII is masked
    normal_res = client.get(f"/telecom/subscribers/{sub.msisdn}")
    assert normal_res.status_code == 200
    data = normal_res.json()
    assert "****" in data["sim"]["imsi"]

    # Defect mode: unmasked PII leaked in trace
    defect_res = client.get(
        f"/telecom/subscribers/{sub.msisdn}",
        headers={"X-Simulate-Defect": TelecomDefectType.CDR_PII_UNMASKED_LOG.value},
    )
    assert defect_res.status_code == 200
    trace = defect_res.json().get("_diagnostic_trace", {})
    assert trace.get("cpni_violation_flag") is True
    assert trace.get("unmasked_imsi") == sub.sim.imsi
    assert trace.get("full_msisdn") == sub.msisdn


# ---------------------------------------------------------------------------
# 3. Knowledge & Domain Pack Contract Tests
# ---------------------------------------------------------------------------

def test_telecom_knowledge_documents():
    """Verify Telecom RAG knowledge documents."""
    docs = get_telecom_rag_docs()
    assert len(docs) == 5
    doc_ids = [d["document_id"] for d in docs]
    assert "TELECOM-FUP-01" in doc_ids
    assert "TELECOM-ROAMING-01" in doc_ids
    assert "TELECOM-BILLING-01" in doc_ids
    assert "TELECOM-PORTABILITY-01" in doc_ids
    assert "TELECOM-CDR-SLA-01" in doc_ids


def test_telecom_domain_pack_metadata_and_catalog():
    """Verify Telecom domain pack contract adherence."""
    pack = domain_registry.get("telecom")
    assert pack is not None
    assert pack.domain_id == "telecom"
    assert pack.has_capability(DomainCapability.API_TESTING)
    assert pack.has_capability(DomainCapability.RAG_AI)
    assert pack.has_capability(DomainCapability.DEFECT_INJECTION)
    assert len(pack.defect_catalog) == 6
    assert "DEF-TC-001" in pack.defect_catalog
    assert "DEF-TC-006" in pack.defect_catalog
