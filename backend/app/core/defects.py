from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from fastapi import Request


class DefectType(str, Enum):
    OVERBOOKING_RACE = "OVERBOOKING_RACE"
    CALCULATION_DRIFT = "CALCULATION_DRIFT"
    STALE_INVENTORY = "STALE_INVENTORY"
    UPSTREAM_GATEWAY_TIMEOUT = "UPSTREAM_GATEWAY_TIMEOUT"
    SCHEMA_CONTRACT_VIOLATION = "SCHEMA_CONTRACT_VIOLATION"


@dataclass
class DefectDefinition:
    id: str
    name: str
    category: str
    affected_endpoint: str
    description: str
    how_to_reproduce: str
    expected_qa_detection: str
    headers: dict = field(default_factory=dict)


DEFECT_REGISTRY: dict[str, DefectDefinition] = {
    DefectType.OVERBOOKING_RACE.value: DefectDefinition(
        id=DefectType.OVERBOOKING_RACE.value,
        name="Seat Inventory Concurrency / Overbooking Bypass",
        category="Concurrency & Integrity",
        affected_endpoint="POST /bookings",
        description=(
            "Simulates a race condition or validation bypass where the system permits a booking "
            "even when requested seats exceed remaining capacity, driving available seats negative."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: OVERBOOKING_RACE' in POST /bookings request.",
        expected_qa_detection=(
            "QA test validates that 'available_seats' invariant (available_seats >= 0) is violated "
            "and that booking completes with status 201 instead of expected 409 Conflict."
        ),
        headers={"X-Simulate-Defect": DefectType.OVERBOOKING_RACE.value},
    ),
    DefectType.CALCULATION_DRIFT.value: DefectDefinition(
        id=DefectType.CALCULATION_DRIFT.value,
        name="Financial Fare Calculation Drift",
        category="Financial Calculation",
        affected_endpoint="POST /bookings, POST /payments",
        description=(
            "Injects an unverified fee or arithmetic calculation drift in total booking or payment amount, "
            "causing total_amount to deviate from base_price * seats."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: CALCULATION_DRIFT' in POST /bookings or POST /payments.",
        expected_qa_detection=(
            "QA test asserts that booking total_amount equals exact itemized price. Fails with "
            "FareDriftAssertionError when calculated total differs from expected base * seats."
        ),
        headers={"X-Simulate-Defect": DefectType.CALCULATION_DRIFT.value},
    ),
    DefectType.STALE_INVENTORY.value: DefectDefinition(
        id=DefectType.STALE_INVENTORY.value,
        name="Stale Cache Inventory Inconsistency",
        category="Caching & Consistency",
        affected_endpoint="GET /search/flights",
        description=(
            "Simulates a stale distributed cache or read replica returning inflated seat availability (999 seats) "
            "that does not match the actual database inventory."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: STALE_INVENTORY' in GET /search/flights.",
        expected_qa_detection=(
            "QA test compares search result seat count against authoritative flight record in PostgreSQL. "
            "Flags cache inconsistency."
        ),
        headers={"X-Simulate-Defect": DefectType.STALE_INVENTORY.value},
    ),
    DefectType.UPSTREAM_GATEWAY_TIMEOUT.value: DefectDefinition(
        id=DefectType.UPSTREAM_GATEWAY_TIMEOUT.value,
        name="Upstream Payment Gateway Timeout Simulation",
        category="Fault Tolerance & Resilience",
        affected_endpoint="POST /payments",
        description=(
            "Simulates an unhandled partner gateway latency or downstream timeout resulting in a 504 Gateway Timeout."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: UPSTREAM_GATEWAY_TIMEOUT' in POST /payments.",
        expected_qa_detection=(
            "QA test validates timeout handling, idempotent retry capability, and fallback error formatting."
        ),
        headers={"X-Simulate-Defect": DefectType.UPSTREAM_GATEWAY_TIMEOUT.value},
    ),
    DefectType.SCHEMA_CONTRACT_VIOLATION.value: DefectDefinition(
        id=DefectType.SCHEMA_CONTRACT_VIOLATION.value,
        name="API Contract Schema Field Omission",
        category="Contract Validation",
        affected_endpoint="GET /bookings/{id}",
        description=(
            "Omits mandatory contract field 'passenger_email' or changes expected structure, "
            "violating OpenAPI schema specifications."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: SCHEMA_CONTRACT_VIOLATION' in GET /bookings/{id}.",
        expected_qa_detection=(
            "QA contract test validates response against Pydantic schema / JSON Schema. Fails on missing required field."
        ),
        headers={"X-Simulate-Defect": DefectType.SCHEMA_CONTRACT_VIOLATION.value},
    ),
}


def get_active_defect(request: Request) -> Optional[DefectDefinition]:
    """Inspect request headers and query parameters for intentional defect simulation flag."""
    defect_id = request.headers.get("x-simulate-defect") or request.query_params.get("simulate_defect")
    if not defect_id:
        return None
    normalized_id = defect_id.strip().upper()
    return DEFECT_REGISTRY.get(normalized_id)
