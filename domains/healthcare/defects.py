"""Healthcare Domain Defect Engineering Catalog.

Adheres strictly to AGENTS.md Section 9 and docs/ROADMAP.md Task 7.1:
- Explicit, documented, reproducible synthetic defect scenarios.
- Demonstrates senior SDET quality engineering detection capabilities.
- Covers HIPAA security, FHIR schema validation, race conditions, clinical dosage precision, and IDOR.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class HealthcareDefectType(str, Enum):
    PHI_EXPOSURE_UNMASKED_SSN = "PHI_EXPOSURE_UNMASKED_SSN"
    FHIR_SCHEMA_VALIDATION_FAILURE = "FHIR_SCHEMA_VALIDATION_FAILURE"
    CONCURRENT_APPOINTMENT_DOUBLE_BOOKING = "CONCURRENT_APPOINTMENT_DOUBLE_BOOKING"
    CLINICAL_DOSAGE_ROUNDING_ERROR = "CLINICAL_DOSAGE_ROUNDING_ERROR"
    RAG_UNGROUNDED_CLINICAL_INTERACTION = "RAG_UNGROUNDED_CLINICAL_INTERACTION"
    IDOR_PATIENT_RECORD_ACCESS = "IDOR_PATIENT_RECORD_ACCESS"


@dataclass
class HealthcareDefectDefinition:
    id: str
    code: str
    name: str
    category: str
    affected_endpoint: str
    description: str
    how_to_reproduce: str
    expected_qa_detection: str
    headers: Dict[str, str] = field(default_factory=dict)


HEALTHCARE_DEFECT_REGISTRY: Dict[str, HealthcareDefectDefinition] = {
    HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value,
        code="DEF-HC-001",
        name="Unencrypted SSN / PHI Exposure in Patient API",
        category="HIPAA Security & Privacy",
        affected_endpoint="POST /healthcare/patients, GET /healthcare/patients/{id}",
        description=(
            "Simulates a critical privacy defect where unmasked 9-digit Social Security Numbers "
            "are returned in the patient resource response, violating HIPAA Safe Harbor (45 CFR § 164.514)."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: PHI_EXPOSURE_UNMASKED_SSN' in patient requests.",
        expected_qa_detection=(
            "QA security test validates that 'ssn_masked' adheres to ***-**-NNNN regex and fails with "
            "PHIExposureAssertionError when unmasked SSN pattern is found in the payload."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value},
    ),
    HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value,
        code="DEF-HC-002",
        name="FHIR R4 Schema Contract Validation Bypass",
        category="Contract & Schema Integrity",
        affected_endpoint="POST /healthcare/patients",
        description=(
            "Bypasses HL7 FHIR Release 4 mandatory element validation, allowing patient resources "
            "with missing family names to be persisted and accepted with HTTP 201 instead of HTTP 422."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: FHIR_SCHEMA_VALIDATION_FAILURE' in POST /healthcare/patients.",
        expected_qa_detection=(
            "QA contract test validates required FHIR attributes and fails when incomplete resource is accepted."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value},
    ),
    HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value,
        code="DEF-HC-003",
        name="Concurrent Practitioner Appointment Double Booking",
        category="Concurrency & Business Logic",
        affected_endpoint="POST /healthcare/appointments",
        description=(
            "Bypasses calendar collision checks, permitting two separate patients to schedule overlapping "
            "consultation intervals with the same practitioner simultaneously."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: CONCURRENT_APPOINTMENT_DOUBLE_BOOKING' in POST /healthcare/appointments.",
        expected_qa_detection=(
            "QA concurrency test asserts HTTP 409 Conflict on overlapping slot; fails if both appointments confirm with HTTP 201."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value},
    ),
    HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value,
        code="DEF-HC-004",
        name="Pediatric Drug Dosage Truncation / Arithmetic Drift",
        category="Clinical Calculation Drift",
        affected_endpoint="POST /healthcare/dosage/calculate",
        description=(
            "Injects an arithmetic floor truncation defect in pediatric weight-based dosage calculation, "
            "causing calculated single_dose_mg to round down to the nearest 10mg instead of exact floating point."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: CLINICAL_DOSAGE_ROUNDING_ERROR' in POST /healthcare/dosage/calculate.",
        expected_qa_detection=(
            "QA test validates calculated dose against weight_kg * mg_per_kg; fails when truncation deviation exceeds 0.01mg tolerance."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value},
    ),
    HealthcareDefectType.RAG_UNGROUNDED_CLINICAL_INTERACTION.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.RAG_UNGROUNDED_CLINICAL_INTERACTION.value,
        code="DEF-HC-005",
        name="Ungrounded Off-Label Clinical Drug Interaction Claim",
        category="AI / RAG Safety & Hallucination",
        affected_endpoint="POST /ai/rag/query",
        description=(
            "Simulates RAG hallucinations where the model generates clinical claims unsupported by ingested "
            "pharmacology protocols, testing automated groundedness metric detection."
        ),
        how_to_reproduce="Query RAG pipeline on ungrounded clinical interaction topics with defect simulation active.",
        expected_qa_detection=(
            "QA RAG quality gate asserts groundedness >= 0.85; fails when ungrounded clinical claims produce groundedness < 0.60."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.RAG_UNGROUNDED_CLINICAL_INTERACTION.value},
    ),
    HealthcareDefectType.IDOR_PATIENT_RECORD_ACCESS.value: HealthcareDefectDefinition(
        id=HealthcareDefectType.IDOR_PATIENT_RECORD_ACCESS.value,
        code="DEF-HC-006",
        name="Insecure Direct Object Reference (IDOR) Patient Record Access",
        category="Security & Authorization",
        affected_endpoint="GET /healthcare/patients/{id}",
        description=(
            "Bypasses practitioner-to-patient assignment authorization checks, allowing an unassigned "
            "practitioner or passenger role to view sensitive clinical records."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: IDOR_PATIENT_RECORD_ACCESS' in GET /healthcare/patients/{id}.",
        expected_qa_detection=(
            "QA authorization test asserts HTTP 403 Forbidden for unauthorized MRN access; fails if HTTP 200 returned."
        ),
        headers={"X-Simulate-Defect": HealthcareDefectType.IDOR_PATIENT_RECORD_ACCESS.value},
    ),
}
