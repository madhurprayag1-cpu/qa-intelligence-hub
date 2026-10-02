"""Healthcare Domain Regression Mapping & PR Diff Presets.

Adheres strictly to AGENTS.md Section 5 and docs/ROADMAP.md Task 7.1:
- Encapsulates Healthcare-specific file pattern matches and test mappings.
- Decouples domain regression rules from the central regression selector.
"""

from typing import Any, Dict, List

HEALTHCARE_REGRESSION_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "healthcare_core": {
        "patterns": ["healthcare", "domains/healthcare"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
        ],
        "tags": ["healthcare", "domain"],
        "ui_specs": [],
    },
    "healthcare_patients": {
        "patterns": ["patient", "mrn", "demographics"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
        ],
        "tags": ["healthcare", "patient", "fhir"],
        "ui_specs": [],
    },
    "healthcare_fhir": {
        "patterns": ["fhir", "hl7", "observation", "vitals", "loinc"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
            "tests/contract/test_openapi_contract.py",
        ],
        "tags": ["healthcare", "fhir", "contract"],
        "ui_specs": [],
    },
    "healthcare_security": {
        "patterns": ["hipaa", "phi", "masking", "ssn", "deidentification"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
            "tests/security/test_security_suite.py",
        ],
        "tags": ["healthcare", "security", "hipaa"],
        "ui_specs": [],
    },
    "healthcare_scheduling": {
        "patterns": ["appointment", "practitioner", "clinical_calendar"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
        ],
        "tags": ["healthcare", "scheduling"],
        "ui_specs": [],
    },
    "healthcare_dosage": {
        "patterns": ["dosage", "pediatric", "pharmacology"],
        "tests": [
            "tests/domains/healthcare/test_healthcare_domain.py",
        ],
        "tags": ["healthcare", "clinical", "dosage"],
        "ui_specs": [],
    },
}

HEALTHCARE_PRESET_PR_DIFFS: Dict[str, List[str]] = {
    "FHIR_PATIENT_ENDPOINT": [
        "backend/app/routers/healthcare.py",
        "domains/healthcare/models.py",
    ],
    "CLINICAL_VITALS_ADAPTER": [
        "domains/healthcare/factories.py",
        "domains/healthcare/knowledge.py",
    ],
    "HIPAA_SECURITY_FILTER": [
        "domains/healthcare/models.py",
        "backend/app/routers/healthcare.py",
    ],
}
