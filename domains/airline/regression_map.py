"""Airline Domain Regression Mapping & PR Diff Presets.

Adheres strictly to the Master Architecture Directive:
- Encapsulates Airline-specific file pattern matches and test mappings.
- Decouples regression pattern knowledge from the core regression selector.
"""

from typing import Any, Dict, List

AIRLINE_REGRESSION_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "payments": {
        "patterns": ["payment", "3ds"],
        "tests": [
            "tests/api/test_payments.py",
            "tests/security/test_security_suite.py",
        ],
        "tags": ["payment", "security"],
        "ui_specs": ["tests/ui/booking_3ds_e2e.spec.ts"],
    },
    "bookings": {
        "patterns": ["booking"],
        "tests": [
            "tests/api/test_bookings.py",
            "tests/api/test_defects.py",
            "tests/security/test_security_suite.py",
        ],
        "tags": ["booking", "defect"],
        "ui_specs": ["tests/ui/booking_3ds_e2e.spec.ts"],
    },
    "search": {
        "patterns": ["flight", "search", "airport", "airline"],
        "tests": [
            "tests/api/test_flight_search.py",
            "tests/security/test_security_suite.py",
        ],
        "tags": ["search", "flight"],
        "ui_specs": ["tests/ui/booking_3ds_e2e.spec.ts"],
    },
}

AIRLINE_PRESET_PR_DIFFS: Dict[str, List[str]] = {
    "PAYMENTS_3DS": [
        "backend/app/routers/payments.py",
        "backend/app/models/payment.py",
    ],
    "AIRPORT_CATALOG": [
        "backend/app/routers/airports.py",
        "backend/app/models/airport.py",
    ],
    "ANCILLARY_FARE": [
        "backend/app/routers/bookings.py",
        "backend/app/routers/flight_search.py",
    ],
}
