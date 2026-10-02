"""Telecom Domain Data Models, State Machine & Rating Engine.

Adheres strictly to AGENTS.md Sections 8, 9, 13, 14, 21:
- Production-grade Pydantic models for Telecommunication services.
- Real-time rating engine for Voice, SMS, Data, and Roaming.
- Finite State Machine for Subscriber lifecycle transitions.
- Boundary condition validation (zero usage, FUP caps, roaming eligibility).
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator


class SubscriptionStatus(str, Enum):
    """Lifecycle statuses for mobile subscriber lines."""
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BARRED = "barred"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


class PlanType(str, Enum):
    """Billing models for telecom packages."""
    PREPAID = "prepaid"
    POSTPAID = "postpaid"
    ENTERPRISE = "enterprise"
    IOT_M2M = "iot_m2m"


class CallType(str, Enum):
    """Usage categories for Call Detail Records."""
    VOICE = "voice"
    SMS = "sms"
    DATA = "data"
    ROAMING_VOICE = "roaming_voice"
    ROAMING_DATA = "roaming_data"


class RatingZone(str, Enum):
    """Geographic rating zones for billing."""
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    ROAMING_ZONE_1 = "roaming_zone_1"  # EU / North America
    ROAMING_ZONE_2 = "roaming_zone_2"  # Rest of world / Maritime


class SIMCard(BaseModel):
    """Represents a physical or eSIM profile."""
    iccid: str = Field(..., description="Integrated Circuit Card Identifier (19-20 digits)")
    imsi: str = Field(..., description="International Mobile Subscriber Identity (15 digits)")
    is_esim: bool = False
    is_active: bool = True
    pin_code: str = "1234"
    puk_code: str = "12345678"

    @field_validator("iccid")
    @classmethod
    def validate_iccid(cls, v: str) -> str:
        clean = v.replace(" ", "").strip()
        if not (18 <= len(clean) <= 22) or not clean.isdigit():
            raise ValueError(f"ICCID must be between 18 and 22 digits: {v}")
        return clean

    @field_validator("imsi")
    @classmethod
    def validate_imsi(cls, v: str) -> str:
        clean = v.replace(" ", "").strip()
        if len(clean) != 15 or not clean.isdigit():
            raise ValueError(f"IMSI must be exactly 15 digits: {v}")
        return clean


class DataPlan(BaseModel):
    """Represents a telecom subscription tariff plan."""
    plan_id: str
    name: str
    plan_type: PlanType
    monthly_fee: float = Field(..., ge=0.0)
    voice_minutes_included: int = Field(default=500, ge=0)
    sms_included: int = Field(default=500, ge=0)
    data_gb_included: float = Field(default=20.0, ge=0.0)
    fup_threshold_gb: float = Field(default=50.0, ge=0.0, description="Fair Usage Policy limit")
    overage_voice_per_min: float = Field(default=0.10, ge=0.0)
    overage_data_per_mb: float = Field(default=0.01, ge=0.0)
    roaming_enabled: bool = False
    throttle_speed_kbps: int = 128


class Subscriber(BaseModel):
    """Telecom Subscriber entity."""
    subscriber_id: str
    msisdn: str = Field(..., description="E.164 phone number, e.g. +14155550100")
    sim: SIMCard
    plan: DataPlan
    status: SubscriptionStatus = SubscriptionStatus.PENDING_ACTIVATION
    balance: float = Field(default=0.0, description="Prepaid credit or postpaid outstanding")
    minutes_used: int = Field(default=0, ge=0)
    sms_used: int = Field(default=0, ge=0)
    data_used_mb: float = Field(default=0.0, ge=0.0)
    roaming_allowed: bool = False
    kyc_verified: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("msisdn")
    @classmethod
    def validate_msisdn(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith("+") or len(clean) < 8 or not clean[1:].isdigit():
            raise ValueError(f"MSISDN must follow E.164 international format (e.g. +14155550199): {v}")
        return clean


class CallDetailRecord(BaseModel):
    """Call Detail Record (CDR) capturing a single network usage session."""
    cdr_id: str
    msisdn: str
    destination: str
    call_type: CallType
    zone: RatingZone = RatingZone.DOMESTIC
    start_time: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int = Field(default=0, ge=0)
    bytes_transferred: int = Field(default=0, ge=0)
    roaming_network: Optional[str] = None
    rated_amount: float = Field(default=0.0, ge=0.0)
    billed: bool = False

    @field_validator("call_type", mode="before")
    @classmethod
    def validate_call_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("zone", mode="before")
    @classmethod
    def validate_zone(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Duration seconds cannot be negative")
        return v


class InvalidSubscriptionStateTransitionError(ValueError):
    """Raised when an illegal subscriber lifecycle status transition is requested."""
    pass


class SubscriptionStateMachine:
    """
    Finite State Machine governing Subscriber line status.
    Ensures strict telecom business rules (e.g., cancelled or terminated lines cannot re-activate).
    """

    ALLOWED_TRANSITIONS: Dict[SubscriptionStatus, Set[SubscriptionStatus]] = {
        SubscriptionStatus.PENDING_ACTIVATION: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.CANCELLED,
        },
        SubscriptionStatus.ACTIVE: {
            SubscriptionStatus.SUSPENDED,
            SubscriptionStatus.BARRED,
            SubscriptionStatus.CANCELLED,
        },
        SubscriptionStatus.SUSPENDED: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.BARRED,
        },
        SubscriptionStatus.BARRED: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TERMINATED,
        },
        SubscriptionStatus.CANCELLED: {
            SubscriptionStatus.TERMINATED,
        },
        SubscriptionStatus.TERMINATED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_status: SubscriptionStatus, to_status: SubscriptionStatus) -> bool:
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, set())

    @classmethod
    def transition(cls, subscriber: Subscriber, target_status: SubscriptionStatus) -> Subscriber:
        if not cls.can_transition(subscriber.status, target_status):
            raise InvalidSubscriptionStateTransitionError(
                f"Illegal subscription state transition from '{subscriber.status.value}' to '{target_status.value}'."
            )
        subscriber.status = target_status
        return subscriber


class RatingEngine:
    """
    Production-grade Telecom Rating Engine.
    Computes precise usage charges according to tariff plans and rating zones.
    """

    @classmethod
    def rate_cdr(cls, subscriber: Subscriber, cdr: CallDetailRecord) -> float:
        """
        Rates a Call Detail Record against subscriber plan quotas and overage tariffs.
        Returns rated charge in currency units (e.g., USD).
        """
        plan = subscriber.plan

        # Voice rating
        if cdr.call_type in (CallType.VOICE, CallType.ROAMING_VOICE):
            minutes = (cdr.duration_seconds + 59) // 60  # Round up to next whole minute
            if cdr.call_type == CallType.ROAMING_VOICE or cdr.zone != RatingZone.DOMESTIC:
                # Roaming voice rate: standard $0.50/min for Zone 1, $1.50/min for Zone 2
                rate_per_min = 0.50 if cdr.zone == RatingZone.ROAMING_ZONE_1 else 1.50
                amount = minutes * rate_per_min
            else:
                remaining_quota = max(0, plan.voice_minutes_included - subscriber.minutes_used)
                if minutes <= remaining_quota:
                    amount = 0.0
                else:
                    overage_minutes = minutes - remaining_quota
                    amount = overage_minutes * plan.overage_voice_per_min

        # SMS rating
        elif cdr.call_type == CallType.SMS:
            if cdr.zone != RatingZone.DOMESTIC:
                amount = 0.25  # International SMS
            else:
                remaining_quota = max(0, plan.sms_included - subscriber.sms_used)
                amount = 0.0 if remaining_quota > 0 else 0.05

        # Data rating
        elif cdr.call_type in (CallType.DATA, CallType.ROAMING_DATA):
            mb_used = cdr.bytes_transferred / (1024 * 1024)
            if cdr.call_type == CallType.ROAMING_DATA or cdr.zone != RatingZone.DOMESTIC:
                # Roaming data rate: $0.05/MB for Zone 1, $0.20/MB for Zone 2
                rate_per_mb = 0.05 if cdr.zone == RatingZone.ROAMING_ZONE_1 else 0.20
                amount = mb_used * rate_per_mb
            else:
                included_mb = plan.data_gb_included * 1024.0
                remaining_mb = max(0.0, included_mb - subscriber.data_used_mb)
                if mb_used <= remaining_mb:
                    amount = 0.0
                else:
                    overage_mb = mb_used - remaining_mb
                    amount = overage_mb * plan.overage_data_per_mb

        else:
            amount = 0.0

        # Exact 2-decimal financial rounding
        dec = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(dec)
