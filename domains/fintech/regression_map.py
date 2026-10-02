"""FinTech Domain Regression Mapping & PR Diff Presets.

Adheres strictly to AGENTS.md Section 5 and docs/ROADMAP.md Task 7.2:
- Encapsulates FinTech-specific file pattern matches and test mappings.
- Decouples domain regression rules from the central regression selector.
"""

from typing import Any, Dict, List

FINTECH_REGRESSION_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "fintech_core": {
        "patterns": ["fintech", "domains/fintech"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
        ],
        "tags": ["fintech", "domain"],
        "ui_specs": [],
    },
    "fintech_ledger": {
        "patterns": ["ledger", "transfer", "balance", "double_entry"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
        ],
        "tags": ["fintech", "ledger", "database"],
        "ui_specs": [],
    },
    "fintech_iso20022": {
        "patterns": ["swift", "iso20022", "pain", "pacs", "iban"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
            "tests/contract/test_openapi_contract.py",
        ],
        "tags": ["fintech", "contract", "iso20022"],
        "ui_specs": [],
    },
    "fintech_kyc": {
        "patterns": ["kyc", "sanctions", "compliance", "aml_compliance"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
        ],
        "tags": ["fintech", "kyc", "compliance"],
        "ui_specs": [],
    },
    "fintech_fraud": {
        "patterns": ["fraud", "velocity", "anomaly"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
        ],
        "tags": ["fintech", "fraud", "security"],
        "ui_specs": [],
    },
    "fintech_exchange": {
        "patterns": ["exchange", "fx", "currency"],
        "tests": [
            "tests/domains/fintech/test_fintech_domain.py",
        ],
        "tags": ["fintech", "fx", "currency"],
        "ui_specs": [],
    },
}

FINTECH_PRESET_PR_DIFFS: Dict[str, List[str]] = {
    "LEDGER_TRANSFER_UPDATE": [
        "backend/app/routers/fintech.py",
        "domains/fintech/models.py",
    ],
    "ISO20022_SCHEMA_UPDATE": [
        "domains/fintech/models.py",
        "domains/fintech/factories.py",
    ],
    "FRAUD_DETECTION_ENGINE": [
        "backend/app/routers/fintech.py",
        "domains/fintech/factories.py",
    ],
}
