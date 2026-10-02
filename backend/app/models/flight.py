from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(primary_key=True)

    flight_number: Mapped[str] = mapped_column(
        String(10),
        index=True,
    )

    airline_id: Mapped[int] = mapped_column(
        ForeignKey("airlines.id"),
        index=True,
    )

    origin_id: Mapped[int] = mapped_column(
        ForeignKey("airports.id"),
        index=True,
    )

    destination_id: Mapped[int] = mapped_column(
        ForeignKey("airports.id"),
        index=True,
    )

    departure_time: Mapped[datetime] = mapped_column(DateTime)
    arrival_time: Mapped[datetime] = mapped_column(DateTime)

    duration_minutes: Mapped[int] = mapped_column(Integer)

    total_seats: Mapped[int] = mapped_column(Integer)
    available_seats: Mapped[int] = mapped_column(Integer)

    base_price: Mapped[float] = mapped_column(Numeric(10, 2))

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )