"""Airline Domain Pack Definition & Registration.

Adheres strictly to the Master Architecture Directive:
- Implements DomainPack protocol for Airline / NDC Aviation.
- Auto-registers with domain_registry.
"""

from domain_registry import DomainCapability, DomainPack, domain_registry
from domains.airline.knowledge import get_airline_knowledge_docs
from domains.airline.regression_map import AIRLINE_REGRESSION_PATTERNS


def get_airline_factories():
    from domains.airline.factories import (
        SyntheticPassenger,
        PassengerFactory,
        BookingPayloadFactory,
        PaymentPayloadFactory,
    )
    return {
        "SyntheticPassenger": SyntheticPassenger,
        "PassengerFactory": PassengerFactory,
        "BookingPayloadFactory": BookingPayloadFactory,
        "PaymentPayloadFactory": PaymentPayloadFactory,
    }


airline_domain_pack = DomainPack(
    domain_id="airline",
    name="Airline / NDC Aviation",
    version="1.0.0",
    description="IATA NDC airline distribution, flight search, seat inventory, and 3DS payment quality engineering.",
    capabilities=[
        DomainCapability.UI_AUTOMATION,
        DomainCapability.API_TESTING,
        DomainCapability.DATABASE_TESTING,
        DomainCapability.CONTRACT_TESTING,
        DomainCapability.RAG_AI,
        DomainCapability.AGENTIC_QA,
        DomainCapability.SECURITY_AUDIT,
        DomainCapability.PERFORMANCE_BENCHMARK,
        DomainCapability.QUALITY_GATE,
        DomainCapability.DEFECT_INJECTION,
    ],
    rag_sources=[
        "AIRLINE-POLICY-01",
        "AIRLINE-BAGGAGE-01",
        "AIRLINE-REFUND-01",
        "AIRLINE-NDC-01",
        "AIRLINE-ANCILLARIES-01",
    ],
    factories_provider=get_airline_factories,
    rag_docs_provider=get_airline_knowledge_docs,
    defect_catalog={
        "DEF-001": "FARE_CALCULATION_OVERCHARGE: Arithmetic discrepancy in base fare + tax calculation",
        "DEF-002": "STALE_SEAT_INVENTORY: Race condition permitting double allocation of seat inventory",
        "DEF-003": "PAYMENT_GATEWAY_TIMEOUT: ACS 3D Secure challenge timeout simulation",
        "DEF-004": "RAG_UNGROUNDED_HALLUCINATION: LLM generates policy claims not grounded in NDC context",
        "DEF-005": "SQL_INJECTION_VULNERABILITY: Raw query concatenation in passenger search parameter",
    },
    regression_patterns=AIRLINE_REGRESSION_PATTERNS,
    metadata={
        "iata_compliance": "NDC 21.3",
        "supported_currencies": ["EUR", "USD", "GBP"],
        "payment_methods_count": 7,
    },
)

# Auto-register with central registry
domain_registry.register(airline_domain_pack)
