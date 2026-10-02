"""Intentional Defect Catalog for the Telecom Domain Pack.

Adheres strictly to AGENTS.md Section 9 (Defect Engineering):
- All defects are documented, reproducible, synthetic, and intended for QE evaluation.
- Defect codes DEF-TC-001 through DEF-TC-006.
"""

from enum import Enum
from typing import Dict


class TelecomDefectType(str, Enum):
    """Enumeration of engineered Telecom defect modes."""
    SIM_SWAP_RACE = "DEF-TC-001"
    CDR_OVERAGE_MISCALCULATION = "DEF-TC-002"
    UNAUTHORIZED_ROAMING_LEAK = "DEF-TC-003"
    DOUBLE_BILLING_CDR_RACE = "DEF-TC-004"
    INVALID_STATE_TRANSITION = "DEF-TC-005"
    CDR_PII_UNMASKED_LOG = "DEF-TC-006"


TELECOM_DEFECT_REGISTRY: Dict[str, str] = {
    TelecomDefectType.SIM_SWAP_RACE.value: (
        "DEF-TC-001: Race condition during concurrent SIM swap allows old and new SIM profiles "
        "to remain concurrently active, enabling unauthorized SMS interception and multi-device clone fraud."
    ),
    TelecomDefectType.CDR_OVERAGE_MISCALCULATION.value: (
        "DEF-TC-002: Data rating engine incorrectly rounds fractional megabytes up to whole gigabytes "
        "prior to tariff multiplication, causing severe overbilling on overage sessions."
    ),
    TelecomDefectType.UNAUTHORIZED_ROAMING_LEAK.value: (
        "DEF-TC-003: Rating engine processes international roaming CDRs for subscribers with "
        "roaming_allowed=False instead of rejecting with BSS authorization error."
    ),
    TelecomDefectType.DOUBLE_BILLING_CDR_RACE.value: (
        "DEF-TC-004: Lack of idempotency verification on duplicate CDR submissions allows "
        "the same network usage record to be rated and billed multiple times."
    ),
    TelecomDefectType.INVALID_STATE_TRANSITION.value: (
        "DEF-TC-005: Subscription state machine allows barred or cancelled subscribers to "
        "reactivate directly to active status or consume network services without audit clearance."
    ),
    TelecomDefectType.CDR_PII_UNMASKED_LOG.value: (
        "DEF-TC-006: Diagnostic responses and audit logs expose unmasked MSISDN, IMSI, and dialed "
        "numbers, violating FCC CPNI (Customer Proprietary Network Information) privacy regulations."
    ),
}
