"""Telecom Domain Regression Mapping & PR Diff Presets.

Adheres strictly to AGENTS.md Section 5:
- Encapsulates Telecom-specific file pattern matches and test mappings.
- Decouples domain regression rules from the central regression selector.
"""

from typing import Any, Dict, List

TELECOM_REGRESSION_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "telecom_core": {
        "patterns": ["telecom", "domains/telecom"],
        "tests": [
            "tests/domains/telecom/test_telecom_domain.py",
        ],
        "tags": ["telecom", "domain"],
        "ui_specs": [],
    },
    "telecom_subscribers": {
        "patterns": ["subscriber", "msisdn", "sim", "iccid", "imsi"],
        "tests": [
            "tests/domains/telecom/test_telecom_domain.py",
        ],
        "tags": ["telecom", "subscriber", "sim_swap"],
        "ui_specs": [],
    },
    "telecom_rating_billing": {
        "patterns": ["cdr", "rating", "tariff", "overage", "fup", "charge"],
        "tests": [
            "tests/domains/telecom/test_telecom_domain.py",
        ],
        "tags": ["telecom", "cdr", "rating", "billing"],
        "ui_specs": [],
    },
    "telecom_roaming": {
        "patterns": ["roaming", "vplmn", "international_zone"],
        "tests": [
            "tests/domains/telecom/test_telecom_domain.py",
        ],
        "tags": ["telecom", "roaming"],
        "ui_specs": [],
    },
    "telecom_cpni_privacy": {
        "patterns": ["cpni", "masked_msisdn", "privacy"],
        "tests": [
            "tests/domains/telecom/test_telecom_domain.py",
            "tests/security/test_security_suite.py",
        ],
        "tags": ["telecom", "security", "cpni"],
        "ui_specs": [],
    },
}

TELECOM_REGRESSION_MAP = TELECOM_REGRESSION_PATTERNS
