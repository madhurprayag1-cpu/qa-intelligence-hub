"""Comprehensive Automated Tests for Healthcare Domain Pack (Phase 7 Task 7.1).

Adheres strictly to AGENTS.md Sections 1-13, 18-21 and docs/ROADMAP.md Task 7.1:
- Verifies dynamic domain registration & capabilities in domain_registry.
- Validates HL7 FHIR Release 4 Pydantic models (Patient, Observation, Appointment).
- Validates HIPAA Safe Harbor (45 CFR § 164.514) de-identification and unmasked PHI detection.
- Tests synthetic test data factories (PatientFactory, ObservationFactory, AppointmentFactory).
- Validates Healthcare SUT REST API endpoints (Patient CRUD, Observations, Scheduling, Dosage).
- Verifies intentional synthetic defect injection & detection (DEF-HC-001 through DEF-HC-006).
- Validates domain-scoped RAG knowledge ingestion and isolated vector retrieval.
- Verifies smart regression selector integration and complete Airline domain isolation.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.healthcare import reset_healthcare_store
from domain_registry import DomainCapability, domain_registry
from domains.healthcare.defects import HEALTHCARE_DEFECT_REGISTRY, HealthcareDefectType
from domains.healthcare.domain_pack import healthcare_domain_pack
from domains.healthcare.factories import (
    AppointmentFactory,
    ClinicalDosageCalculator,
    ObservationFactory,
    PatientFactory,
)
from domains.healthcare.knowledge import (
    HEALTHCARE_KNOWLEDGE_DOCS,
    get_healthcare_knowledge_docs,
)
from domains.healthcare.models import (
    FHIRAppointment,
    FHIRObservation,
    FHIRPatient,
    HIPAAMasker,
)
from regression_selector import select_regression_tests


@pytest.fixture(autouse=True)
def clean_healthcare_store():
    """Ensures clean in-memory state for every test."""
    reset_healthcare_store()
    yield
    reset_healthcare_store()


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Domain Pack Registration & Metadata Invariants ---

def test_healthcare_domain_pack_registered():
    """Verify Healthcare domain pack auto-registers with central registry and adheres to contract."""
    assert domain_registry.is_domain_supported("healthcare")
    pack = domain_registry.get("healthcare")
    assert pack is not None
    assert pack.domain_id == "healthcare"
    assert "HL7 FHIR" in pack.name
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
        assert pack.has_capability(cap), f"Missing capability {cap} in Healthcare domain pack"

    # Assert metadata & regulatory standards
    meta = pack.metadata
    assert meta["fhir_standard"] == "HL7 FHIR Release 4 (4.0.1)"
    assert "Safe Harbor" in meta["hipaa_compliance_mode"]
    assert "LOINC" in meta["coding_systems"]
    assert meta["safe_harbor_identifiers_count"] == 18

    # Assert defect catalog
    assert len(pack.defect_catalog) >= 6
    assert "DEF-HC-001" in pack.defect_catalog
    assert "DEF-HC-002" in pack.defect_catalog
    assert "DEF-HC-003" in pack.defect_catalog
    assert "DEF-HC-004" in pack.defect_catalog
    assert "DEF-HC-006" in pack.defect_catalog


# --- 2. Synthetic Test Data Factories ---

def test_patient_factory_build_and_batch():
    """Verify PatientFactory generates deterministic, synthetic, and safe patient entities."""
    patient = PatientFactory.build(index=0)
    assert patient.mrn.startswith("MRN-HC-")
    assert patient.first_name
    assert patient.last_name
    assert "@qahub-health.io" in patient.email
    assert patient.ssn_masked.startswith("***-**-")

    batch = PatientFactory.build_batch(5)
    assert len(batch) == 5
    # Verify uniqueness of MRNs and emails across batch
    mrns = {p.mrn for p in batch}
    emails = {p.email for p in batch}
    assert len(mrns) == 5
    assert len(emails) == 5


def test_patient_factory_boundary_and_security_variants():
    """Verify elderly, pediatric, and XSS security patient variants."""
    elderly = PatientFactory.build_boundary_elderly()
    assert elderly["birthDate"] == "1932-05-14"

    pediatric = PatientFactory.build_boundary_pediatric()
    assert pediatric["birthDate"] == "2022-08-20"

    xss = PatientFactory.build_security_xss()
    assert "<script>" in xss["name"][0]["text"]
    assert "</script>" in xss["name"][0]["family"]


# --- 3. HL7 FHIR Release 4 Schema Validation ---

def test_fhir_patient_schema_validation():
    """Verify valid patient dictionary adheres strictly to FHIR R4 Patient schema."""
    valid_payload = PatientFactory.build_fhir_patient()
    validated = FHIRPatient.model_validate(valid_payload)
    assert validated.resourceType == "Patient"
    assert validated.id.startswith("MRN-HC-")
    assert validated.active is True
    assert len(validated.name) >= 1
    assert validated.gender in ["male", "female", "other", "unknown"]

    # Incomplete schema missing name must raise validation error
    invalid_payload = PatientFactory.build_invalid_missing_name()
    with pytest.raises(Exception):
        FHIRPatient.model_validate(invalid_payload)


def test_fhir_observation_loinc_validation():
    """Verify observation factory produces valid LOINC-coded FHIR Observation resources."""
    vitals = ObservationFactory.build_vital_signs(
        patient_id="MRN-HC-100001",
        heart_rate=76.0,
        systolic=120.0,
        diastolic=80.0,
        spo2=99.0,
    )
    assert len(vitals) == 3

    # Check Heart Rate
    hr_obs = vitals[0]
    validated_hr = FHIRObservation.model_validate(hr_obs)
    assert validated_hr.code.coding[0].code == ObservationFactory.LOINC_HEART_RATE
    assert validated_hr.valueQuantity.value == 76.0

    # Check Blood Pressure Panel
    bp_obs = vitals[1]
    validated_bp = FHIRObservation.model_validate(bp_obs)
    assert validated_bp.code.coding[0].code == ObservationFactory.LOINC_BLOOD_PRESSURE
    assert len(validated_bp.component) == 2

    # Check SpO2
    spo2_obs = vitals[2]
    validated_spo2 = FHIRObservation.model_validate(spo2_obs)
    assert validated_spo2.code.coding[0].code == ObservationFactory.LOINC_OXYGEN_SAT
    assert validated_spo2.valueQuantity.value == 99.0


def test_fhir_appointment_schema_validation():
    """Verify appointment factory produces valid FHIR Appointment resources."""
    appt_payload = AppointmentFactory.build(
        patient_id="MRN-HC-100001",
        practitioner_id="PRAC-HC-001",
        duration_minutes=45,
    )
    validated = FHIRAppointment.model_validate(appt_payload)
    assert validated.resourceType == "Appointment"
    assert validated.status == "booked"
    assert len(validated.participant) == 2


# --- 4. HIPAA Safe Harbor De-Identification & Masking ---

def test_hipaa_safe_harbor_masking():
    """Verify HIPAA Safe Harbor SSN & phone masking utility."""
    # Formatted SSN
    assert HIPAAMasker.mask_ssn("123-45-6789") == "***-**-6789"
    # Unformatted 9-digit SSN
    assert HIPAAMasker.mask_ssn("987654321") == "***-**-4321"
    # Empty / None
    assert HIPAAMasker.mask_ssn(None) == "***-**-0000"

    # Phone masking
    assert HIPAAMasker.mask_phone("+15551234567") == "***-***-4567"

    # PHI Leak Scanner: Clean masked record should have 0 violations
    clean_patient = PatientFactory.build_fhir_patient()
    violations = HIPAAMasker.detect_unmasked_phi(clean_patient)
    assert len(violations) == 0

    # PHI Leak Scanner: Unmasked raw SSN must be flagged
    leaked_patient = PatientFactory.build_phi_leak_vulnerable()
    violations = HIPAAMasker.detect_unmasked_phi(leaked_patient)
    assert len(violations) > 0
    assert any("SSN" in v for v in violations)


# --- 5. Healthcare REST API Lifecycle ---

def test_healthcare_api_patient_crud(client: TestClient):
    """Verify POST and GET /healthcare/patients endpoints."""
    patient_payload = PatientFactory.build_fhir_patient()
    mrn = patient_payload["id"]

    # 1. Create Patient
    create_resp = client.post("/healthcare/patients", json=patient_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["id"] == mrn
    assert created_data["ssn_masked"].startswith("***-**-")

    # 2. Get Patient
    get_resp = client.get(f"/healthcare/patients/{mrn}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == mrn

    # 3. Not Found
    missing_resp = client.get("/healthcare/patients/MRN-NON-EXISTENT")
    assert missing_resp.status_code == 404


def test_healthcare_api_observations_flow(client: TestClient):
    """Verify recording and querying vital signs observations."""
    vitals = ObservationFactory.build_vital_signs(patient_id="MRN-HC-4001")

    # Post each observation
    for obs in vitals:
        resp = client.post("/healthcare/observations", json=obs)
        assert resp.status_code == 201

    # Query observations for patient
    list_resp = client.get("/healthcare/observations?patient_id=MRN-HC-4001")
    assert list_resp.status_code == 200
    obs_list = list_resp.json()
    assert len(obs_list) == 3


def test_healthcare_api_appointment_scheduling_and_conflict(client: TestClient):
    """Verify appointment scheduling and automated conflict detection (409 Conflict)."""
    base_appt = AppointmentFactory.build(
        patient_id="MRN-HC-5001",
        practitioner_id="PRAC-HC-007",
        start_time="2026-10-15T10:00:00",
        duration_minutes=30,
    )

    # 1. First appointment schedules successfully
    resp1 = client.post("/healthcare/appointments", json=base_appt)
    assert resp1.status_code == 201

    # 2. Second overlapping appointment with same practitioner must be rejected with 409
    conflicting_appt = AppointmentFactory.build_conflicting_slot(
        base_appointment=base_appt,
        new_patient_id="MRN-HC-5002",
    )
    resp2 = client.post("/healthcare/appointments", json=conflicting_appt)
    assert resp2.status_code == 409
    assert "Practitioner calendar conflict" in resp2.json()["detail"]


def test_healthcare_api_pediatric_dosage_calculation(client: TestClient):
    """Verify weight-based pediatric clinical dosage calculation."""
    payload = {
        "patient_id": "MRN-HC-6001",
        "drug_name": "Amoxicillin",
        "patient_weight_kg": 15.0,
        "recommended_mg_per_kg": 20.0,
        "frequency_hours": 8,
    }
    resp = client.post("/healthcare/dosage/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["single_dose_mg"] == 300.0  # 15.0 * 20.0
    assert data["daily_total_mg"] == 900.0  # 300.0 * 3 doses/day
    assert data["precision_verified"] is True
    assert data["warning"] is None


# --- 6. Intentional Defect Injection & Detection Verification ---

def test_defect_def_hc_001_phi_exposure_detected(client: TestClient):
    """
    DEF-HC-001 Verification:
    Simulates PHI_EXPOSURE_UNMASKED_SSN defect and confirms QA security validation catches it.
    """
    vulnerable_patient = PatientFactory.build_phi_leak_vulnerable()

    # Normal behavior: SSN is masked
    clean_resp = client.post("/healthcare/patients", json=vulnerable_patient)
    assert clean_resp.status_code == 201
    assert clean_resp.json()["ssn_masked"].startswith("***-**-")

    # Injected defect: leaks unmasked SSN
    defect_resp = client.post(
        "/healthcare/patients",
        json=vulnerable_patient,
        headers={"X-Simulate-Defect": HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value},
    )
    assert defect_resp.status_code == 201
    leaked_data = defect_resp.json()

    # QA Security Assertion: Must detect unmasked SSN violation
    violations = HIPAAMasker.detect_unmasked_phi(leaked_data)
    assert len(violations) > 0, "QA security check failed: Unmasked SSN leak was NOT detected!"


def test_defect_def_hc_002_fhir_schema_violation_detected(client: TestClient):
    """
    DEF-HC-002 Verification:
    Simulates FHIR_SCHEMA_VALIDATION_FAILURE defect and verifies contract enforcement.
    """
    invalid_patient = PatientFactory.build_invalid_missing_name()

    # Normal behavior: Must reject with 422 Unprocessable Entity
    normal_resp = client.post("/healthcare/patients", json=invalid_patient)
    assert normal_resp.status_code == 422

    # Injected defect: Bypasses schema validation, returning 201
    defect_resp = client.post(
        "/healthcare/patients",
        json=invalid_patient,
        headers={"X-Simulate-Defect": HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value},
    )
    assert defect_resp.status_code == 201
    # QA Contract Assertion: Resource missing name element violates FHIR R4
    assert len(defect_resp.json().get("name", [])) == 0


def test_defect_def_hc_003_double_booking_race_detected(client: TestClient):
    """
    DEF-HC-003 Verification:
    Simulates CONCURRENT_APPOINTMENT_DOUBLE_BOOKING defect and confirms concurrency detection.
    """
    base_appt = AppointmentFactory.build(
        patient_id="MRN-HC-7001",
        practitioner_id="PRAC-HC-009",
        start_time="2026-11-01T09:00:00",
        duration_minutes=30,
    )
    client.post("/healthcare/appointments", json=base_appt)

    conflicting_appt = AppointmentFactory.build_conflicting_slot(
        base_appointment=base_appt,
        new_patient_id="MRN-HC-7002",
    )

    # Injected defect: Allows double booking with 201 instead of 409
    defect_resp = client.post(
        "/healthcare/appointments",
        json=conflicting_appt,
        headers={"X-Simulate-Defect": HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value},
    )
    assert defect_resp.status_code == 201
    # QA Concurrency Assertion: Detects that two active appointments share identical slot
    assert defect_resp.json()["status"] == "booked"


def test_defect_def_hc_004_dosage_truncation_drift_detected(client: TestClient):
    """
    DEF-HC-004 Verification:
    Simulates CLINICAL_DOSAGE_ROUNDING_ERROR and confirms arithmetic drift detection.
    """
    payload = {
        "patient_id": "MRN-HC-8001",
        "drug_name": "Ceftriaxone",
        "patient_weight_kg": 12.5,
        "recommended_mg_per_kg": 15.0,  # Expected exact dose: 187.5 mg
    }

    # Normal behavior: Exact dose 187.5 mg
    normal_resp = client.post("/healthcare/dosage/calculate", json=payload)
    assert normal_resp.status_code == 200
    assert normal_resp.json()["single_dose_mg"] == 187.5
    assert normal_resp.json()["precision_verified"] is True

    # Injected defect: Truncates to nearest 10mg floor (180.0 mg)
    defect_resp = client.post(
        "/healthcare/dosage/calculate",
        json=payload,
        headers={"X-Simulate-Defect": HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value},
    )
    assert defect_resp.status_code == 200
    data = defect_resp.json()
    # QA Clinical Precision Assertion: Must detect drift and underdosing warning
    assert data["single_dose_mg"] == 180.0
    assert data["precision_verified"] is False
    assert data["warning"] == "ARITHMETIC_PRECISION_DRIFT_DETECTED"


def test_defect_def_hc_006_idor_access_detected(client: TestClient):
    """
    DEF-HC-006 Verification:
    Simulates IDOR_PATIENT_RECORD_ACCESS defect and confirms authorization vulnerability detection.
    """
    patient = PatientFactory.build_fhir_patient()
    mrn = patient["id"]
    client.post("/healthcare/patients", json=patient)

    # Normal behavior: Unauthorized role receives 403 Forbidden
    unauth_resp = client.get(f"/healthcare/patients/{mrn}", headers={"X-User-Role": "unauthorized"})
    assert unauth_resp.status_code == 403

    # Injected defect: Permits unauthorized access with 200 OK
    defect_resp = client.get(
        f"/healthcare/patients/{mrn}",
        headers={
            "X-User-Role": "unauthorized",
            "X-Simulate-Defect": HealthcareDefectType.IDOR_PATIENT_RECORD_ACCESS.value,
        },
    )
    # QA Security Assertion: IDOR flaw detected when unauthorized role receives 200 OK
    assert defect_resp.status_code == 200


def test_healthcare_defects_catalog_endpoint(client: TestClient):
    """Verify GET /healthcare/defects returns all documented healthcare defect scenarios."""
    resp = client.get("/healthcare/defects")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 6
    defect_ids = [d["id"] for d in catalog]
    assert HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value in defect_ids
    assert HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value in defect_ids
    assert HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value in defect_ids
    assert HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value in defect_ids


# --- 7. Domain RAG Knowledge Base & Cross-Domain Isolation ---

def test_healthcare_knowledge_docs_provider():
    """Verify synthetic healthcare knowledge provider conforms to contract."""
    docs = get_healthcare_knowledge_docs()
    assert len(docs) == 5

    doc_ids = [d["document_id"] for d in docs]
    assert "HEALTHCARE-FHIR-01" in doc_ids
    assert "HEALTHCARE-HIPAA-01" in doc_ids
    assert "HEALTHCARE-CLINICAL-01" in doc_ids
    assert "HEALTHCARE-APPOINTMENT-01" in doc_ids
    assert "HEALTHCARE-DOSAGE-01" in doc_ids

    for doc in docs:
        assert doc["metadata"]["domain"] == "healthcare"
        assert len(doc["text"]) > 50


@pytest.mark.anyio
async def test_healthcare_rag_isolated_query():
    """Verify domain-scoped RAG query returns only healthcare clinical evidence."""
    from rag import RAGPipeline
    from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider

    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
    )
    # Ingest healthcare domain knowledge
    loaded_count = pipeline.load_domain_knowledge(healthcare_domain_pack)
    assert loaded_count == 5

    # Query with domain="healthcare"
    res = await pipeline.query("What are the normal adult vital signs ranges?", domain="healthcare")
    assert res.refusal is False
    assert len(res.retrieved_chunks) > 0
    for chunk in res.retrieved_chunks:
        assert chunk.metadata.get("domain") == "healthcare"


# --- 8. Smart Regression Selector Integration & Airline Invariant ---

def test_healthcare_smart_regression_selector():
    """Verify changes to healthcare domain files trigger healthcare regression tests."""
    plan = select_regression_tests(["domains/healthcare/factories.py", "domains/healthcare/models.py"])
    assert "tests/domains/healthcare/test_healthcare_domain.py" in plan.selected_test_files
    assert any("healthcare" in tag for tag in plan.selected_tags)


def test_airline_regression_remains_intact():
    """Verify Airline regression mappings remain fully intact with zero interference."""
    plan = select_regression_tests(["backend/app/routers/payments.py"])
    assert "tests/api/test_payments.py" in plan.selected_test_files
    assert "payment" in plan.selected_tags
    assert plan.playwright_command is not None
    assert "booking_3ds_e2e.spec.ts" in plan.playwright_command
