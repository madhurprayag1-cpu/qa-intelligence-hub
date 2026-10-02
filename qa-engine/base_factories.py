"""Reusable Synthetic Test Data Primitives & Factory Core.

Adheres strictly to the Master Architecture Directive:
- Domain-independent synthetic data generators.
- Clean separation between generic person/payment/boundary primitives
  and domain-specific models (Passenger, Patient, Customer, Subscriber).
- 100% synthetic, deterministic, and safe for public portfolio execution.
- No real customer/employer data or confidential records.
"""

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class SyntheticPerson:
    """Universal synthetic person identity."""
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str = "+10000000000"
    country_code: str = "US"


class PersonGenerator:
    """Deterministic synthetic person generator with boundary & security variants."""

    _FIRST_NAMES = ["Alex", "Elena", "Dimitris", "Sofia", "Marcus", "Chloe", "Nikos", "Maria", "Liam", "Emma"]
    _LAST_NAMES = ["Papadopoulos", "Smith", "Kowalski", "Dupont", "Rossi", "Ioannidis", "Vargas", "Chen", "Mueller"]

    @classmethod
    def generate(
        cls,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email_domain: str = "qahub.io",
        index: int = 0,
    ) -> SyntheticPerson:
        first = first_name or cls._FIRST_NAMES[index % len(cls._FIRST_NAMES)]
        last = last_name or cls._LAST_NAMES[index % len(cls._LAST_NAMES)]
        full = f"{first} {last}"
        safe_tag = secrets.token_hex(3)
        email = f"{first.lower()}.{last.lower()}.{safe_tag}@{email_domain}"

        return SyntheticPerson(
            first_name=first,
            last_name=last,
            full_name=full,
            email=email,
        )

    @classmethod
    def generate_xss(cls, email_domain: str = "qahub.io") -> SyntheticPerson:
        return SyntheticPerson(
            first_name="<script>",
            last_name="alert('XSS')</script>",
            full_name="<script>alert('XSS')</script>",
            email=f"xss_eval_{secrets.token_hex(2)}@{email_domain}",
        )

    @classmethod
    def generate_boundary_long(cls, length: int = 255) -> SyntheticPerson:
        return SyntheticPerson(
            first_name="A" * (length // 2),
            last_name="B" * (length // 2),
            full_name="A" * length,
            email=f"longname_{secrets.token_hex(2)}@qahub.io",
        )


class IdentifierGenerator:
    """Generates deterministic synthetic identifiers and correlation tokens."""

    @classmethod
    def generate_reference(cls, prefix: str = "REF", length: int = 8) -> str:
        token = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
        return f"{prefix}-{token}"

    @classmethod
    def generate_alphanumeric(cls, length: int = 10) -> str:
        return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

    @classmethod
    def generate_numeric(cls, length: int = 8) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(length))


class PaymentInstrumentGenerator:
    """
    Simulates PCI DSS compliant payment tokens and synthetic card fixtures.
    Never uses real credit card numbers or banking secrets.
    """

    @classmethod
    def generate_card(
        cls,
        brand: str = "VISA",
        requires_3ds: bool = False,
    ) -> Dict[str, Any]:
        """Returns synthetic card fixture for testing."""
        # Standard synthetic test prefixes: 4000 0000 0000 XXXX
        last_four = IdentifierGenerator.generate_numeric(4)
        return {
            "brand": brand,
            "masked_pan": f"****-****-****-{last_four}",
            "last_four": last_four,
            "expiry_month": "12",
            "expiry_year": str(datetime.utcnow().year + 3),
            "cvv": "123",
            "requires_3ds": requires_3ds,
            "token": f"tok_synth_{secrets.token_hex(8)}",
        }


class SecurityPayloadGenerator:
    """Security injection test payloads across SQLi, XSS, and command injection."""

    SQLI_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "UNION SELECT NULL, NULL, NULL --",
        "admin' --",
        "1; SELECT pg_sleep(5); --",
    ]

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert('xss')",
        "<svg onload=alert(document.cookie)>",
    ]

    @classmethod
    def get_sqli_payload(cls, index: int = 0) -> str:
        return cls.SQLI_PAYLOADS[index % len(cls.SQLI_PAYLOADS)]

    @classmethod
    def get_xss_payload(cls, index: int = 0) -> str:
        return cls.XSS_PAYLOADS[index % len(cls.XSS_PAYLOADS)]
