from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class AncillarySelection(BaseModel):
    baggage_tier: int = Field(default=0, ge=0, le=2, description="0=Carry-on, 1=1 Checked, 2=2 Checked")
    seat_preference: str = Field(default="STANDARD", description="STANDARD, WINDOW_AISLE, EXTRA_LEGROOM")
    meal_preference: str = Field(default="STANDARD", description="STANDARD, GOURMET, VEGAN, GLUTEN_FREE, HALAL, KOSHER")


class BookingCreate(BaseModel):
    flight_id: int
    passenger_name: str = Field(min_length=2, max_length=120)
    passenger_email: EmailStr
    seats: int = Field(default=1, ge=1, le=9)
    payment_method: str = Field(default="CARD", min_length=2, max_length=30)
    ancillaries: AncillarySelection = Field(default_factory=AncillarySelection)


class BookingResponse(BaseModel):
    id: int
    reference: str
    flight_id: int
    passenger_name: str
    passenger_email: EmailStr
    seats: int
    base_fare: float = 0.0
    ancillary_amount: float = 0.0
    total_amount: float
    status: str
    ancillaries: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class BookingCancelResponse(BaseModel):
    booking_id: int
    reference: str
    previous_status: str
    current_status: str
    seats_released: int
    refund_status: str
    refund_amount: float
