"""Synthetic Test Data Factories.

Backward-compatibility module re-exporting Airline domain factories from
domains.airline.factories while providing core access to base_factories.
"""

from typing import Any, Dict, Optional

from domains.airline.factories import (
    SyntheticPassenger,
    PassengerFactory,
    BookingPayloadFactory,
    PaymentPayloadFactory,
)


def get_domain_factories(domain_id: Optional[str] = None) -> Dict[str, Any]:
    """Dynamically resolves factories for the specified or currently active domain."""
    from domain_registry import domain_registry
    if domain_id:
        pack = domain_registry.get(domain_id)
        if pack and pack.factories_provider:
            return pack.factories_provider()
        return {}
    return domain_registry.get_active_factories()


__all__ = [
    "SyntheticPassenger",
    "PassengerFactory",
    "BookingPayloadFactory",
    "PaymentPayloadFactory",
    "get_domain_factories",
]

