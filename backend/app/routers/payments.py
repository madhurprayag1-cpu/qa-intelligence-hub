import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.defects import DefectType, get_active_defect
from app.core.auth import User, get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.booking import Booking
from app.models.payment import (
    Payment,
    PaymentMethod,
    PaymentStatus,
    ThreeDSStatus,
)
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=201,
)
async def create_payment(
    payload: PaymentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.environment.lower() in {"production", "prod"} and current_user.email != "passenger@qahub.io":
        raise HTTPException(status_code=503, detail="Payments are disabled until production authentication is configured")
    active_defect = get_active_defect(request)

    # Defect Hook: UPSTREAM_GATEWAY_TIMEOUT simulates 504 partner gateway latency/failure
    if active_defect and active_defect.id == DefectType.UPSTREAM_GATEWAY_TIMEOUT.value:
        raise HTTPException(
            status_code=504,
            detail="Upstream payment gateway timeout",
        )

    booking = db.get(Booking, payload.booking_id)

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )
    if current_user.role == "passenger" and booking.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: booking belongs to another user")

    existing_payment = db.execute(
        select(Payment).where(
            Payment.booking_id == booking.id
        )
    ).scalar_one_or_none()

    if existing_payment:
        raise HTTPException(
            status_code=409,
            detail="Payment already exists for this booking",
        )

    is_3ds = payload.method == PaymentMethod.CREDIT_CARD_3DS

    # Defect Hook: CALCULATION_DRIFT injects unauthorized amount difference
    charged_amount = (
        float(booking.total_amount) + 75.50
        if active_defect and active_defect.id == DefectType.CALCULATION_DRIFT.value
        else booking.total_amount
    )

    payment = Payment(
        booking_id=booking.id,
        amount=charged_amount,
        currency="EUR",
        method=payload.method.value,
        status=PaymentStatus.PROCESSING.value,
        three_ds_required=is_3ds,
        three_ds_status=(
            payload.three_ds_result.value
            if is_3ds
            else ThreeDSStatus.NOT_REQUIRED.value
        ),
        authorization_status="PENDING",
        transaction_reference=(
            "TXN-" + secrets.token_hex(6).upper()
        ),
        provider_reference=(
            "PROV-" + secrets.token_hex(6).upper()
        ),
    )

    # 3DS payment flow
    if is_3ds:
        if payload.three_ds_result == ThreeDSStatus.SUCCESS:
            payment.status = PaymentStatus.PAID.value
            payment.authorization_status = "AUTHORIZED"
            booking.status = "PAID"

        elif payload.three_ds_result == ThreeDSStatus.FAILED:
            payment.status = PaymentStatus.FAILED.value
            payment.authorization_status = "DECLINED"
            payment.failure_code = "3DS_AUTH_FAILED"
            payment.failure_reason = "3DS authentication failed"

        elif payload.three_ds_result == ThreeDSStatus.TIMEOUT:
            payment.status = PaymentStatus.TIMEOUT.value
            payment.authorization_status = "PENDING"
            payment.failure_code = "3DS_TIMEOUT"
            payment.failure_reason = "3DS authentication timed out"

        elif payload.three_ds_result == ThreeDSStatus.CANCELLED:
            payment.status = PaymentStatus.CANCELLED.value
            payment.authorization_status = "CANCELLED"
            payment.failure_code = "3DS_CANCELLED"
            payment.failure_reason = "Customer cancelled 3DS authentication"

        else:
            payment.status = PaymentStatus.PENDING.value

    # Non-3DS payment flow
    else:
        if payload.method == PaymentMethod.CASH:
            payment.status = PaymentStatus.PAID.value
            payment.authorization_status = "AUTHORIZED"

        elif payload.method in {
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.EASY_PAY,
            PaymentMethod.UPI,
            PaymentMethod.WALLET,
        }:
            payment.status = PaymentStatus.PAID.value
            payment.authorization_status = "AUTHORIZED"

        booking.status = "PAID"

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


@router.get(
    "/{booking_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == "passenger" and booking.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: booking belongs to another user")
    payment = db.execute(
        select(Payment).where(
            Payment.booking_id == booking_id
        )
    ).scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return payment