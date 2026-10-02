"""Synthetic Healthcare Clinical & Regulatory QA Knowledge Base.

Adheres to AGENTS.md Sections 8, 10, 18, 19 and docs/ROADMAP.md Task 7.1:
- 100% synthetic, public-safe clinical guidance and interoperability standards.
- Strictly decoupled from reusable AI core and vector search indexers.
- Serves as the domain knowledge provider for multi-domain RAG retrieval and evaluation.
"""

from typing import Any, Dict, List


HEALTHCARE_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    {
        "document_id": "HEALTHCARE-FHIR-01",
        "text": (
            "The Healthcare clinical exchange engine strictly implements HL7 FHIR Release 4 (4.0.1) schemas. "
            "The Patient resource represents clinical demographics, requiring at least one official name and unique "
            "Medical Record Number (MRN) identifier. The Observation resource models clinical measurements including vital "
            "signs coded with Logical Observation Identifiers Names and Codes (LOINC) and units from the Unified Code for Units "
            "of Measure (UCUM). Direct API operations utilize RESTful HTTP semantics: POST to create with status 201 Created, "
            "GET for resource retrieval with status 200 OK, and 422 Unprocessable Entity for schema contract validation failures."
        ),
        "metadata": {
            "title": "HL7 FHIR R4 Standards & Resource Interoperability",
            "domain": "healthcare",
            "source": "HEALTHCARE-FHIR-01",
            "category": "standards",
            "version": "4.0.1",
        },
    },
    {
        "document_id": "HEALTHCARE-HIPAA-01",
        "text": (
            "Healthcare privacy governance complies with HIPAA Privacy and Security Rules under 45 CFR § 164.514(b)(2). "
            "Under the Safe Harbor de-identification method, 18 explicit direct identifiers must be redacted, masked, or removed "
            "before clinical data dissemination. Social Security Numbers (SSN) must never be transmitted in cleartext and must "
            "be masked to the format ***-**-NNNN in non-administrative responses. Unencrypted transmission of 9-digit SSNs or "
            "direct patient contact details constitutes a critical HIPAA security violation."
        ),
        "metadata": {
            "title": "HIPAA Safe Harbor De-Identification & PHI Security Standards",
            "domain": "healthcare",
            "source": "HEALTHCARE-HIPAA-01",
            "category": "compliance",
            "version": "1.0",
        },
    },
    {
        "document_id": "HEALTHCARE-CLINICAL-01",
        "text": (
            "Clinical triage monitors adult vital signs against validated clinical reference ranges. "
            "Standard adult resting heart rate spans 60 to 100 beats per minute. Normal blood pressure is systolic below 120 mmHg "
            "and diastolic below 80 mmHg. Arterial oxygen saturation (SpO2) must remain at or above 95% on room air. "
            "A systolic blood pressure exceeding 180 mmHg or diastolic exceeding 120 mmHg triggers an immediate Hypertensive Crisis alert. "
            "An oxygen saturation measurement below 90% constitutes acute Hypoxemia requiring urgent clinical intervention."
        ),
        "metadata": {
            "title": "Clinical Vital Signs Triage & Alert Threshold Protocol",
            "domain": "healthcare",
            "source": "HEALTHCARE-CLINICAL-01",
            "category": "clinical",
            "version": "1.0",
        },
    },
    {
        "document_id": "HEALTHCARE-APPOINTMENT-01",
        "text": (
            "Outpatient scheduling protocols mandate strict concurrency controls on practitioner calendars. "
            "A practitioner can only hold one active clinical consultation slot per time interval; double-booking the same "
            "practitioner across overlapping start and end times must be rejected with an HTTP 409 Conflict error. "
            "Cancellations must be processed with a minimum 24-hour lead time, upon which the cancelled appointment slot is "
            "synchronously returned to the open schedule inventory for immediate re-allocation."
        ),
        "metadata": {
            "title": "Outpatient Scheduling & Practitioner Concurrency Governance",
            "domain": "healthcare",
            "source": "HEALTHCARE-APPOINTMENT-01",
            "category": "scheduling",
            "version": "1.0",
        },
    },
    {
        "document_id": "HEALTHCARE-DOSAGE-01",
        "text": (
            "Pediatric pharmacology calculations require strict weight-based precision using kilograms. "
            "Single dose administration equals patient weight in kilograms multiplied by the recommended mg/kg dosage factor. "
            "Calculations must preserve full floating-point precision rounded to two decimal places; integer floor or ceiling "
            "truncation is strictly prohibited as it leads to dangerous sub-therapeutic underdosing or toxic overdosing. "
            "Total daily dosages must never exceed the established adult maximum daily ceiling for any given pharmaceutical agent."
        ),
        "metadata": {
            "title": "Pediatric Weight-Based Dosage Calculation & Precision Standards",
            "domain": "healthcare",
            "source": "HEALTHCARE-DOSAGE-01",
            "category": "pharmacology",
            "version": "1.0",
        },
    },
]


def get_healthcare_knowledge_docs() -> List[Dict[str, Any]]:
    """Provider function returning synthetic knowledge documents for the Healthcare domain pack."""
    return HEALTHCARE_KNOWLEDGE_DOCS
