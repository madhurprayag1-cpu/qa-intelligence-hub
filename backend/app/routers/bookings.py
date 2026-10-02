import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.ancillaries import calculate_ancillary_breakdown, get_ancillary_catalog
from app.core.auth import User, get_current_user
from app.core.config import settings
from app.core.defects import DefectType, get_active_defect
from app.db.database import get_db
from app.models.booking import Booking
from app.models.flight import Flight
from app.models.payment import Payment
from app.schemas.booking import BookingCancelResponse, BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/ancillaries/catalog")
async def get_ancillaries_catalog():
    """Retrieve catalog of available ancillary options (baggage, seating, meals)."""
    return get_ancillary_catalog()


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    payload: BookingCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.environment.lower() in {"production", "prod"}:
        raise HTTPException(status_code=503, detail="Booking is disabled until production authentication is configured")
    active_defect = get_active_defect(request)

    flight = db.get(Flight, payload.flight_id)
    if not flight or not flight.active:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Defect Hook: OVERBOOKING_RACE bypasses seat availability check
    if active_defect and active_defect.id == DefectType.OVERBOOKING_RACE.value:
        pass  # Intentionally skip seat count validation to simulate overbooking defect
    else:
        if flight.available_seats < payload.seats:
            raise HTTPException(status_code=409, detail="Insufficient seat availability")

    flight.available_seats -= payload.seats

    # Calculate itemized ancillary charges
    try:
        ancillary_total, breakdown = calculate_ancillary_breakdown(
            baggage_tier=payload.ancillaries.baggage_tier,
            seat_preference=payload.ancillaries.seat_preference,
            meal_preference=payload.ancillaries.meal_preference,
            seats=payload.seats,
        )
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))

    base_fare = round(float(flight.base_price) * payload.seats, 2)

    # Defect Hook: CALCULATION_DRIFT distorts price arithmetic
    if active_defect and active_defect.id == DefectType.CALCULATION_DRIFT.value:
        total = round(base_fare * 1.35 + 49.99 + ancillary_total, 2)
    else:
        total = round(base_fare + ancillary_total, 2)

    booking = Booking(
        reference="QAH-" + secrets.token_hex(4).upper(),
        flight_id=flight.id,
        passenger_name=payload.passenger_name,
        passenger_email=payload.passenger_email,
        owner_user_id=current_user.id,
        seats=payload.seats,
        base_fare=base_fare,
        ancillary_amount=ancillary_total,
        total_amount=total,
        status="CONFIRMED",
        ancillaries=breakdown,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/{booking_id}")
async def get_booking_by_id(
    booking_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_defect = get_active_defect(request)
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # IDOR Protection: Passenger role can only inspect their own bookings
    if current_user.role == "passenger":
        if booking.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: IDOR protection prevented access to another passenger's booking",
            )

    # Defect Hook: SCHEMA_CONTRACT_VIOLATION intentionally violates OpenAPI schema
    if active_defect and active_defect.id == DefectType.SCHEMA_CONTRACT_VIOLATION.value:
        return JSONResponse(
            status_code=200,
            content={
                "id": str(booking.id),  # type drift
                # Omit required passenger_email field
                "reference": booking.reference,
                "flight_id": booking.flight_id,
                "passenger_name": booking.passenger_name,
                "seats": booking.seats,
                "total_amount": float(booking.total_amount),
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None,
            },
        )

    return BookingResponse.model_validate(booking)


@router.get("/reference/{reference}", response_model=BookingResponse)
async def get_booking_by_reference(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.execute(
        select(Booking).where(Booking.reference == reference.upper())
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role == "passenger" and booking.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: booking belongs to another user")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # IDOR Protection: Passenger role can only cancel their own bookings
    if current_user.role == "passenger":
        if booking.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: IDOR protection prevented cancellation of another passenger's booking",
            )

    if booking.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Booking is already cancelled")

    flight = db.get(Flight, booking.flight_id)
    seats_to_release = booking.seats

    # Restore seat inventory on flight
    if flight:
        flight.available_seats += seats_to_release

    prev_status = booking.status
    booking.status = "CANCELLED"

    # Check payment status to issue refund if already paid
    payment = db.execute(
        select(Payment).where(Payment.booking_id == booking.id)
    ).scalar_one_or_none()

    refund_status = "NOT_APPLICABLE"
    refund_amount = 0.0

    if payment and payment.status in ["PAID", "AUTHORIZED"]:
        payment.status = "REFUNDED"
        refund_status = "REFUNDED"
        refund_amount = float(booking.total_amount)

    db.commit()

    return BookingCancelResponse(
        booking_id=booking.id,
        reference=booking.reference,
        previous_status=prev_status,
        current_status="CANCELLED",
        seats_released=seats_to_release,
        refund_status=refund_status,
        refund_amount=refund_amount,
    )


