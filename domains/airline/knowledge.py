"""Synthetic Airline QA Knowledge Base.

Adheres to AGENTS.md Sections 8 & 10:
- Synthetic, public-safe aviation knowledge documents.
- Strictly decoupled from reusable AI core.
- Serves as the domain knowledge provider for RAG vector indexing.
"""

from typing import Any, Dict, List


AIRLINE_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    {
        "document_id": "AIRLINE-POLICY-01",
        "text": (
            "All bookings on QA Intelligence Hub can be paid using credit card, debit card, "
            "cash, easy pay, UPI, wallet, or 3DS credit card. "
            "For 3D Secure credit cards, cardholders complete an Access Control Server (ACS) challenge. "
            "If authentication fails with 3DS_AUTH_FAILED, the booking remains confirmed but unpaid. "
            "Overbooking seats beyond available inventory produces an HTTP 409 conflict error."
        ),
        "metadata": {
            "title": "Booking, Payment & 3D Secure Terms",
            "domain": "airline",
            "source": "AIRLINE-POLICY-01",
            "category": "payments",
            "version": "1.0",
        },
    },
    {
        "document_id": "AIRLINE-BAGGAGE-01",
        "text": (
            "Passengers are entitled to one complimentary cabin baggage item up to 8kg with maximum "
            "dimensions of 55x40x23cm. Standard checked baggage up to 23kg costs 35 EUR per bag. "
            "Excess baggage over 23kg or additional pieces cost 45 EUR per piece. "
            "Sporting equipment and special items must be declared at least 24 hours prior to departure."
        ),
        "metadata": {
            "title": "Cabin & Checked Baggage Regulations",
            "domain": "airline",
            "source": "AIRLINE-BAGGAGE-01",
            "category": "baggage",
            "version": "1.0",
        },
    },
    {
        "document_id": "AIRLINE-REFUND-01",
        "text": (
            "Voluntary cancellations on refundable fares trigger automated refunds within 48 business "
            "hours to the original payment instrument. Non-refundable promotional tickets receive non-expiring "
            "travel credit vouchers. Upon cancellation, reserved seat inventory is immediately and synchronously "
            "restored to available flight capacity in the inventory database."
        ),
        "metadata": {
            "title": "Cancellation, Refund & Seat Inventory Restitution",
            "domain": "airline",
            "source": "AIRLINE-REFUND-01",
            "category": "refunds",
            "version": "1.0",
        },
    },
    {
        "document_id": "AIRLINE-NDC-01",
        "text": (
            "The airline reservation engine implements IATA NDC 21.3 schemas. The AirShopping service exposes "
            "multi-carrier flight offer discovery. The OfferPrice service guarantees 30-minute fare and seat locks "
            "for selected offers. The OrderCreate service generates confirmed Passenger Name Records (PNR) and "
            "OrderIDs. The OrderCancel service executes synchronous reservation teardown and refund dispatch."
        ),
        "metadata": {
            "title": "IATA NDC 21.3 Distribution Protocols",
            "domain": "airline",
            "source": "AIRLINE-NDC-01",
            "category": "standards",
            "version": "21.3",
        },
    },
    {
        "document_id": "AIRLINE-ANCILLARIES-01",
        "text": (
            "Standard seat selection is complimentary during online check-in. Extra legroom and exit row seating "
            "options cost between 25 EUR and 45 EUR. Priority boarding privileges cost 15 EUR per passenger. "
            "Gourmet in-flight dining meal bundles range from 12 EUR to 28 EUR and must be confirmed prior to flight lock."
        ),
        "metadata": {
            "title": "Ancillary Packages, Seat Selection & In-Flight Dining",
            "domain": "airline",
            "source": "AIRLINE-ANCILLARIES-01",
            "category": "ancillaries",
            "version": "1.0",
        },
    },
]


def get_airline_knowledge_docs() -> List[Dict[str, Any]]:
    """Provider function returning synthetic knowledge documents for the Airline domain pack."""
    return AIRLINE_KNOWLEDGE_DOCS
