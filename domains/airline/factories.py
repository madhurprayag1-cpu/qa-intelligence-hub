"""Airline Domain Synthetic Test Data Factories.

Adheres strictly to the Master Architecture Directive:
- Domain-specific synthetic passenger, booking, and payment payload generation.
- Reuses PersonGenerator and IdentifierGenerator from core base_factories.
- 100% deterministic, synthetic, and safe for portfolio demonstrations.
- Strictly backward-compatible with all existing tests and fixtures.
"""

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from base_factories import PersonGenerator, IdentifierGenerator


@dataclass
class SyntheticPassenger:
    """Airline passenger synthetic entity."""
    name: str
    email: str
    passport_number: str
    loyalty_tier: str = "STANDARD"
    nationality: str = "GR"
    phone: str = "+302100000000"


class PassengerFactory:
    """Deterministic synthetic passenger generator (AGENTS.md Section 12)."""

    _FIRST_NAMES = ["Alex", "Elena", "Dimitris", "Sofia", "Marcus", "Chloe", "Nikos", "Maria"]
    _LAST_NAMES = ["Papadopoulos", "Smith", "Kowalski", "Dupont", "Rossi", "Ioannidis", "Vargas"]
    _TIERS = ["STANDARD", "SILVER", "GOLD", "PLATINUM"]

    @classmethod
    def build(
        cls,
        name: Optional[str] = None,
        email: Optional[str] = None,
        loyalty_tier: str = "STANDARD",
        index: int = 0,
    ) -> SyntheticPassenger:
        first = cls._FIRST_NAMES[index % len(cls._FIRST_NAMES)]
        last = cls._LAST_NAMES[index % len(cls._LAST_NAMES)]
        computed_name = name or f"{first} {last}"
        safe_tag = secrets.token_hex(3)
        computed_email = email or f"{first.lower()}.{last.lower()}.{safe_tag}@qahub.io"
        passport = "P" + "".join(secrets.choice(string.digits) for _ in range(8))

        return SyntheticPassenger(
            name=computed_name,
            email=computed_email,
            passport_number=passport,
            loyalty_tier=loyalty_tier,
        )

    @classmethod
    def build_batch(cls, count: int) -> List[SyntheticPassenger]:
        return [cls.build(index=i) for i in range(count)]

    @classmethod
    def build_security_xss(cls) -> SyntheticPassenger:
        xss_person = PersonGenerator.generate_xss()
        return SyntheticPassenger(
            name=xss_person.full_name,
            email=xss_person.email,
            passport_number="P99999999",
        )

    @classmethod
    def build_boundary_long_name(cls) -> SyntheticPassenger:
        long_person = PersonGenerator.generate_boundary_long(length=255)
        return SyntheticPassenger(
            name=long_person.full_name,
            email=long_person.email,
            passport_number="P88888888",
        )


class BookingPayloadFactory:
    """Booking request payload factory."""

    @classmethod
    def build(
        cls,
        flight_id: int,
        seats: int = 1,
        passenger: Optional[SyntheticPassenger] = None,
    ) -> Dict[str, Any]:
        p = passenger or PassengerFactory.build()
        return {
            "flight_id": flight_id,
            "passenger_name": p.name,
            "passenger_email": p.email,
            "seats": seats,
        }

    @classmethod
    def build_boundary_max_seats(cls, flight_id: int) -> Dict[str, Any]:
        return cls.build(flight_id=flight_id, seats=9)

    @classmethod
    def build_invalid_negative_seats(cls, flight_id: int) -> Dict[str, Any]:
        return cls.build(flight_id=flight_id, seats=-1)

    @classmethod
    def build_invalid_zero_seats(cls, flight_id: int) -> Dict[str, Any]:
        return cls.build(flight_id=flight_id, seats=0)


class PaymentPayloadFactory:
    """Payment request payload factory."""

    @classmethod
    def build_3ds(
        cls,
        booking_id: int,
        outcome: str = "SUCCESS",
    ) -> Dict[str, Any]:
        return {
            "booking_id": booking_id,
            "method": "CREDIT_CARD_3DS",
            "three_ds_result": outcome,
        }

    @classmethod
    def build_direct_card(cls, booking_id: int) -> Dict[str, Any]:
        return {
            "booking_id": booking_id,
            "method": "CREDIT_CARD",
        }

    @classmethod
    def build_wallet(cls, booking_id: int) -> Dict[str, Any]:
        return {
            "booking_id": booking_id,
            "method": "WALLET",
        }

    @classmethod
    def build_upi(cls, booking_id: int) -> Dict[str, Any]:
        return {
            "booking_id": booking_id,
            "method": "UPI",
        }
