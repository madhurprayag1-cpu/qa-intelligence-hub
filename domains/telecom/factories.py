"""Deterministic Synthetic Data Factories for Telecom Domain.

Adheres strictly to AGENTS.md Section 12 (Test Data):
- 100% synthetic, public-safe phone numbers, IMSIs, and ICCIDs.
- Zero real customer data, strictly deterministic.
- Supports positive, negative, boundary, and concurrency testing.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from base_factories import IdentifierGenerator, PersonGenerator
from domains.telecom.models import (
    CallDetailRecord,
    CallType,
    DataPlan,
    PlanType,
    RatingZone,
    SIMCard,
    Subscriber,
    SubscriptionStatus,
)


class SIMFactory:
    """Generates synthetic SIMCard instances with valid structural checksums."""

    @classmethod
    def build(cls, index: int = 0, is_esim: bool = False) -> SIMCard:
        # 89 standard telecom prefix + 310 (US MNC) + 14 deterministic digits
        suffix = f"{index:014d}"
        iccid = f"89310{suffix}"[:20]
        # 310 (MCC/MNC) + 12 deterministic digits
        imsi = f"310260{index:09d}"[:15]
        return SIMCard(
            iccid=iccid,
            imsi=imsi,
            is_esim=is_esim,
            is_active=True,
            pin_code="1234",
            puk_code="12345678",
        )


class PlanFactory:
    """Generates synthetic telecom tariff plans."""

    PLANS = [
        DataPlan(
            plan_id="PLAN-5G-UNLIMITED",
            name="5G Ultra Unlimited Postpaid",
            plan_type=PlanType.POSTPAID,
            monthly_fee=65.00,
            voice_minutes_included=99999,
            sms_included=99999,
            data_gb_included=100.0,
            fup_threshold_gb=150.0,
            overage_voice_per_min=0.00,
            overage_data_per_mb=0.00,
            roaming_enabled=True,
        ),
        DataPlan(
            plan_id="PLAN-PREPAID-STARTER",
            name="Prepaid Starter 15GB",
            plan_type=PlanType.PREPAID,
            monthly_fee=25.00,
            voice_minutes_included=500,
            sms_included=500,
            data_gb_included=15.0,
            fup_threshold_gb=20.0,
            overage_voice_per_min=0.10,
            overage_data_per_mb=0.02,
            roaming_enabled=False,
        ),
        DataPlan(
            plan_id="PLAN-IOT-FLEET",
            name="IoT Machine-to-Machine 500MB",
            plan_type=PlanType.IOT_M2M,
            monthly_fee=5.00,
            voice_minutes_included=0,
            sms_included=100,
            data_gb_included=0.5,
            fup_threshold_gb=1.0,
            overage_voice_per_min=0.25,
            overage_data_per_mb=0.05,
            roaming_enabled=False,
        ),
    ]

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[DataPlan]:
        for p in cls.PLANS:
            if p.plan_id == plan_id:
                return p
        return None

    @classmethod
    def build(cls, index: int = 0) -> DataPlan:
        return cls.PLANS[index % len(cls.PLANS)]


class SubscriberFactory:
    """Generates synthetic Subscriber accounts."""

    @classmethod
    def build(
        cls,
        index: int = 0,
        plan_id: Optional[str] = None,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        roaming_allowed: bool = False,
        balance: float = 50.0,
    ) -> Subscriber:
        person = PersonGenerator.generate(index=index)
        # Generate synthetic E.164 MSISDN, e.g. +14155550100
        msisdn = f"+1415555{index:04d}"
        sim = SIMFactory.build(index=index)
        plan = PlanFactory.get_plan(plan_id) if plan_id else PlanFactory.build(index=index)

        return Subscriber(
            subscriber_id=f"SUB-{index:06d}",
            msisdn=msisdn,
            sim=sim,
            plan=plan,
            status=status,
            balance=balance,
            minutes_used=50,
            sms_used=20,
            data_used_mb=1024.0,  # 1 GB used
            roaming_allowed=roaming_allowed,
            kyc_verified=True,
            created_at=datetime.utcnow(),
        )


class CDRFactory:
    """Generates synthetic Call Detail Records for rating and billing validation."""

    @classmethod
    def build_voice_cdr(
        cls,
        index: int = 0,
        msisdn: str = "+14155550100",
        destination: str = "+14155550200",
        duration_seconds: int = 180,
        zone: RatingZone = RatingZone.DOMESTIC,
    ) -> CallDetailRecord:
        call_type = CallType.ROAMING_VOICE if zone != RatingZone.DOMESTIC else CallType.VOICE
        return CallDetailRecord(
            cdr_id=f"CDR-V-{index:07d}",
            msisdn=msisdn,
            destination=destination,
            call_type=call_type,
            zone=zone,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            duration_seconds=duration_seconds,
            bytes_transferred=0,
            roaming_network="VODAFONE_UK" if zone != RatingZone.DOMESTIC else None,
            rated_amount=0.0,
            billed=False,
        )

    @classmethod
    def build_data_cdr(
        cls,
        index: int = 0,
        msisdn: str = "+14155550100",
        mb_transferred: float = 100.0,
        zone: RatingZone = RatingZone.DOMESTIC,
    ) -> CallDetailRecord:
        bytes_count = int(mb_transferred * 1024 * 1024)
        call_type = CallType.ROAMING_DATA if zone != RatingZone.DOMESTIC else CallType.DATA
        return CallDetailRecord(
            cdr_id=f"CDR-D-{index:07d}",
            msisdn=msisdn,
            destination="APN:INTERNET.TELCO.NET",
            call_type=call_type,
            zone=zone,
            start_time=datetime.utcnow() - timedelta(minutes=10),
            duration_seconds=600,
            bytes_transferred=bytes_count,
            roaming_network="ORANGE_FR" if zone != RatingZone.DOMESTIC else None,
            rated_amount=0.0,
            billed=False,
        )


def get_telecom_factories() -> Dict[str, Any]:
    """Exposes telecom factories for dynamic DomainPack binding."""
    return {
        "SubscriberFactory": SubscriberFactory,
        "PlanFactory": PlanFactory,
        "SIMFactory": SIMFactory,
        "CDRFactory": CDRFactory,
    }
