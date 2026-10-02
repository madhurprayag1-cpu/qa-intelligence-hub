from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    passenger_name: Mapped[str] = mapped_column(String(120))
    passenger_email: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    seats: Mapped[int] = mapped_column(Integer, default=1)
    base_fare: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    ancillary_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(30), default="CONFIRMED", index=True)
    ancillaries: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
