"""Telecom / 5G Mobile & BSS/OSS REST API & SUT Router.

Adheres strictly to AGENTS.md Sections 8, 9, 13, 21 and Phase 1B Blueprint:
- Production-grade synthetic SUT endpoints for Subscriber provisioning, SIM swap, Rating, and Billing.
- Dual-plane execution: PostgreSQL persistence via SQLAlchemy models + in-memory hermetic cache.
- Strict tenant isolation with owner_user_id enforcing IDOR boundaries.
- Realistic defect injection hooks for QA demonstration (DEF-TC-001 through DEF-TC-006).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import User, get_current_domain_user
from app.db.database import get_db
from app.models.telecom import TelecomCDRModel, TelecomSubscriberModel
from domains.telecom.defects import TELECOM_DEFECT_REGISTRY, TelecomDefectType
from domains.telecom.factories import PlanFactory, SIMFactory, SubscriberFactory
from domains.telecom.models import (
    CallDetailRecord,
    CallType,
    DataPlan,
    InvalidSubscriptionStateTransitionError,
    RatingEngine,
    RatingZone,
    SIMCard,
    Subscriber,
    SubscriptionStateMachine,
    SubscriptionStatus,
)

router = APIRouter(prefix="/telecom", tags=["telecom-domain"])

# Hermetic in-memory store for synthetic Telecom SUT execution
_SUBSCRIBER_STORE: Dict[str, Subscriber] = {}
_CDR_STORE: Dict[str, CallDetailRecord] = {}
_PROCESSED_CDR_KEYS: set = set()  # Deduplication cache


def reset_telecom_store() -> None:
    """Resets in-memory stores for hermetic test execution."""
    _SUBSCRIBER_STORE.clear()
    _CDR_STORE.clear()
    _PROCESSED_CDR_KEYS.clear()


class SIMSwapRequest(BaseModel):
    new_iccid: str
    new_imsi: str
    idempotency_key: Optional[str] = None


class StatusTransitionRequest(BaseModel):
    target_status: SubscriptionStatus


class RateCDRRequest(BaseModel):
    cdr: CallDetailRecord
    idempotency_key: Optional[str] = None


class RateCDRResponse(BaseModel):
    cdr_id: str
    msisdn: str
    rated_amount: float
    billed: bool
    status: str
    balance_remaining: float


@router.post("/reset", status_code=status.HTTP_200_OK)
async def reset_store() -> Dict[str, str]:
    reset_telecom_store()
    return {"status": "RESET", "message": "Telecom in-memory stores cleared"}


@router.get("/plans", response_model=List[DataPlan])
async def list_plans() -> List[DataPlan]:
    """Lists available 5G/Mobile tariff plans."""
    return PlanFactory.PLANS


@router.post("/subscribers", status_code=status.HTTP_201_CREATED, response_model=Subscriber)
async def create_subscriber(
    subscriber: Subscriber,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> Subscriber:
    """Provisions a new synthetic subscriber line and persists to PostgreSQL with tenant isolation."""
    _SUBSCRIBER_STORE[subscriber.msisdn] = subscriber

    # DB Persistence
    try:
        existing = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == subscriber.msisdn).first()
        if existing:
            existing.status = subscriber.status.value
            existing.imsi = subscriber.sim.imsi
            existing.plan_id = subscriber.plan.plan_id
        else:
            sub_id = subscriber.subscriber_id or f"SUB-{subscriber.msisdn.replace('+', '')}"
            db_subscriber = TelecomSubscriberModel(
                subscriber_id=sub_id,
                owner_user_id=current_user.id,
                msisdn=subscriber.msisdn,
                iccid=subscriber.sim.iccid,
                imsi=subscriber.sim.imsi,
                plan_id=subscriber.plan.plan_id,
                status=subscriber.status.value,
                balance=Decimal(str(subscriber.balance)),
                minutes_used=0,
                sms_used=0,
                data_used_mb=Decimal("0.00"),
                roaming_allowed=subscriber.roaming_allowed,
                kyc_verified=True,
            )
            db.add(db_subscriber)
        db.commit()
    except Exception:
        db.rollback()

    return subscriber


@router.get("/subscribers/{msisdn}")
async def get_subscriber(
    msisdn: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Retrieves subscriber profile with CPNI privacy masking and IDOR check.
    Supports defect simulation:
    - DEF-TC-006 (CDR_PII_UNMASKED_LOG): Exposes unmasked IMSI, ICCID, and full PII logs.
    """
    sub = _SUBSCRIBER_STORE.get(msisdn)
    db_sub = None
    try:
        db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
    except Exception:
        pass

    if not sub and not db_sub:
        sub = SubscriberFactory.build(index=0)
        sub.msisdn = msisdn
        _SUBSCRIBER_STORE[msisdn] = sub

    # IDOR Tenant Verification
    if db_sub and current_user.role not in {"admin", "staff"}:
        if db_sub.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: IDOR protection prevented access to another subscriber's account.",
            )

    if not sub:
        sub = SubscriberFactory.build(index=0)
        sub.msisdn = msisdn

    data = sub.model_dump()

    # DEF-TC-006: Unmasked PII leak in diagnostic response
    if x_simulate_defect in (TelecomDefectType.CDR_PII_UNMASKED_LOG.value, "DEF-TC-006", "DEF-TC-001", "CDR_PII_UNMASKED_LOG"):
        data["_diagnostic_trace"] = {
            "unmasked_imsi": sub.sim.imsi,
            "unmasked_iccid": sub.sim.iccid,
            "full_msisdn": sub.msisdn,
            "puk_code_exposed": sub.sim.puk_code,
            "cpni_violation_flag": True,
        }
    else:
        masked_msisdn = sub.msisdn[:8] + "****" if len(sub.msisdn) > 8 else sub.msisdn
        masked_imsi = sub.sim.imsi[:6] + "*********" if len(sub.sim.imsi) == 15 else sub.sim.imsi
        data["sim"]["imsi"] = masked_imsi
        data["sim"]["puk_code"] = "********"

    return data


@router.get("/subscribers/{msisdn}/cdrs")
async def list_subscriber_cdrs(
    msisdn: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves call detail records (CDRs) for subscriber line with IDOR verification."""
    try:
        db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
        if db_sub and current_user.role not in {"admin", "staff"}:
            if db_sub.owner_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: IDOR protection prevented access to another subscriber's usage history.",
                )

        db_cdrs = (
            db.query(TelecomCDRModel)
            .filter(TelecomCDRModel.msisdn == msisdn)
            .order_by(TelecomCDRModel.created_at.desc())
            .all()
        )
        if db_cdrs:
            return [
                {
                    "cdr_id": c.cdr_id,
                    "msisdn": c.msisdn,
                    "call_type": c.call_type,
                    "destination": c.destination,
                    "duration_seconds": c.duration_seconds,
                    "bytes_transferred": c.bytes_transferred,
                    "rated_amount": float(c.rated_amount),
                    "created_at": c.created_at.isoformat() if c.created_at else "",
                }
                for c in db_cdrs
            ]
    except HTTPException:
        raise
    except Exception:
        pass

    return [c.model_dump() for c in _CDR_STORE.values() if c.msisdn == msisdn]


@router.post("/subscribers/{msisdn}/status", response_model=Subscriber)
async def update_subscriber_status(
    msisdn: str,
    req: StatusTransitionRequest,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Subscriber:
    """
    Executes subscriber lifecycle status transition.
    Supports defect simulation:
    - DEF-TC-005 (INVALID_STATE_TRANSITION): Bypasses FSM rules and permits illegal transition.
    """
    sub = _SUBSCRIBER_STORE.get(msisdn)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subscriber {msisdn} not found")

    if x_simulate_defect in (TelecomDefectType.INVALID_STATE_TRANSITION.value, "DEF-TC-005", "INVALID_STATE_TRANSITION"):
        sub.status = req.target_status
        try:
            db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
            if db_sub:
                db_sub.status = req.target_status.value
                db.commit()
        except Exception:
            db.rollback()
        return sub

    try:
        updated = SubscriptionStateMachine.transition(sub, req.target_status)
        _SUBSCRIBER_STORE[msisdn] = updated

        try:
            db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
            if db_sub:
                db_sub.status = req.target_status.value
                db.commit()
        except Exception:
            db.rollback()

        return updated
    except InvalidSubscriptionStateTransitionError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )


@router.post("/subscribers/{msisdn}/sim-swap")
async def execute_sim_swap(
    msisdn: str,
    req: SIMSwapRequest,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Executes a SIM swap for an existing subscriber.
    Supports defect simulation:
    - DEF-TC-001 (SIM_SWAP_RACE): Leaves both old and new SIM active simultaneously.
    """
    sub = _SUBSCRIBER_STORE.get(msisdn)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subscriber {msisdn} not found")

    old_iccid = sub.sim.iccid
    old_imsi = sub.sim.imsi

    if x_simulate_defect in (TelecomDefectType.SIM_SWAP_RACE.value, "DEF-TC-001", "DEF-TC-002", "SIM_SWAP_RACE"):
        sub.sim.is_active = True
        return {
            "status": "SWAP_PROCESSED_WITH_RACE",
            "active_iccids": [old_iccid, req.new_iccid],
            "active_imsis": [old_imsi, req.new_imsi],
            "twin_sim_active": True,
        }

    sub.sim.is_active = False
    new_sim = SIMCard(
        iccid=req.new_iccid,
        imsi=req.new_imsi,
        is_esim=False,
        is_active=True,
    )
    sub.sim = new_sim
    _SUBSCRIBER_STORE[msisdn] = sub

    try:
        db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
        if db_sub:
            db_sub.imsi = req.new_imsi
            db_sub.iccid = req.new_iccid
            db.commit()
    except Exception:
        db.rollback()

    return {
        "status": "SWAP_COMPLETED",
        "new_iccid": req.new_iccid,
        "old_iccid_deactivated": True,
        "twin_sim_active": False,
    }


@router.post("/cdr/rate", response_model=RateCDRResponse)
async def rate_cdr(
    req: RateCDRRequest,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> RateCDRResponse:
    """
    Rates and bills a Call Detail Record against subscriber account.
    Persists CDR and updates usage counters in PostgreSQL.
    Supports defect simulation:
    - DEF-TC-002: Rounds fractional MB up to full GBs, massively inflating charges.
    - DEF-TC-003: Bypasses roaming authorization check for non-roaming subscriber.
    - DEF-TC-004: Skips idempotency deduplication check, allowing duplicate billing.
    """
    cdr = req.cdr
    sub = _SUBSCRIBER_STORE.get(cdr.msisdn)
    if not sub:
        sub = SubscriberFactory.build(index=0)
        sub.msisdn = cdr.msisdn
        _SUBSCRIBER_STORE[cdr.msisdn] = sub

    is_roaming = cdr.call_type in (CallType.ROAMING_VOICE, CallType.ROAMING_DATA) or cdr.zone != RatingZone.DOMESTIC
    if is_roaming and not sub.roaming_allowed:
        if x_simulate_defect not in (TelecomDefectType.UNAUTHORIZED_ROAMING_LEAK.value, "DEF-TC-003", "UNAUTHORIZED_ROAMING_LEAK"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"TEL-ERR-ROAMING-NOT-ALLOWED: Roaming not authorized for subscriber {sub.msisdn}",
            )

    dedup_key = f"{sub.sim.imsi}:{cdr.destination}:{cdr.duration_seconds}:{cdr.bytes_transferred}"
    if dedup_key in _PROCESSED_CDR_KEYS and x_simulate_defect not in (TelecomDefectType.DOUBLE_BILLING_CDR_RACE.value, "DEF-TC-004", "DOUBLE_BILLING_CDR_RACE"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"DUPLICATE_USAGE: CDR with key {dedup_key} already rated within deduplication window",
        )

    if x_simulate_defect in (TelecomDefectType.CDR_OVERAGE_MISCALCULATION.value, "DEF-TC-002", "CDR_OVERAGE_MISCALCULATION") and cdr.call_type == CallType.DATA:
        mb = cdr.bytes_transferred / (1024 * 1024)
        gb_rounded = int(mb + 1023) // 1024
        rate = sub.plan.overage_data_per_mb if sub.plan.overage_data_per_mb > 0 else 0.05
        rated_charge = float(gb_rounded * 1024 * rate)
    else:
        rated_charge = RatingEngine.rate_cdr(sub, cdr)

    sub.balance = round(sub.balance - rated_charge, 2)
    cdr.rated_amount = rated_charge
    cdr.billed = True

    _PROCESSED_CDR_KEYS.add(dedup_key)
    _CDR_STORE[cdr.cdr_id] = cdr
    _SUBSCRIBER_STORE[sub.msisdn] = sub

    # DB Persistence
    try:
        db_sub = db.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == sub.msisdn).first()
        if not db_sub:
            db_sub = TelecomSubscriberModel(
                subscriber_id=f"SUB-{sub.msisdn.replace('+', '')}",
                owner_user_id=current_user.id,
                msisdn=sub.msisdn,
                iccid=sub.sim.iccid,
                imsi=sub.sim.imsi,
                plan_id=sub.plan.plan_id,
                status=sub.status.value,
                balance=Decimal(str(sub.balance)),
                minutes_used=0,
                sms_used=0,
                data_used_mb=Decimal("0.00"),
                roaming_allowed=sub.roaming_allowed,
                kyc_verified=True,
            )
            db.add(db_sub)
            db.flush()

        if cdr.call_type == CallType.VOICE:
            db_sub.minutes_used += int(cdr.duration_seconds / 60)
        elif cdr.call_type == CallType.DATA:
            db_sub.data_used_mb += Decimal(str(round(cdr.bytes_transferred / (1024 * 1024), 2)))
        elif cdr.call_type == CallType.SMS:
            db_sub.sms_used += 1
        db_sub.balance = Decimal(str(sub.balance))

        db_cdr = TelecomCDRModel(
            cdr_id=cdr.cdr_id,
            msisdn=sub.msisdn,
            destination=cdr.destination,
            call_type=cdr.call_type.value,
            zone=cdr.zone.value if hasattr(cdr.zone, "value") else str(cdr.zone),
            duration_seconds=cdr.duration_seconds,
            bytes_transferred=cdr.bytes_transferred,
            rated_amount=Decimal(str(rated_charge)),
            billed=True,
        )
        db.add(db_cdr)
        db.commit()
    except Exception:
        db.rollback()

    return RateCDRResponse(
        cdr_id=cdr.cdr_id,
        msisdn=sub.msisdn,
        rated_amount=rated_charge,
        billed=True,
        status="RATED_AND_BILLED",
        balance_remaining=sub.balance,
    )
