"""repair calendar-year boundary coverage for extended flight schedules

Revision ID: f3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-10-08 00:00:00.000000
"""

from datetime import date, datetime, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.seed_flights import generate_schedule_flights


revision: str = "f3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _shift_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # Handles Feb 29 when moving to a non-leap year.
        return value.replace(year=value.year + years, day=28)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    flights = sa.Table("flights", metadata, autoload_with=bind)
    airlines = sa.Table("airlines", metadata, autoload_with=bind)
    airports = sa.Table("airports", metadata, autoload_with=bind)

    today = date.today()
    boundary_dates = {
        _shift_years(today, -2),
        _shift_years(today, 3),
    }

    airline_ids = {
        row.code: row.id
        for row in bind.execute(sa.select(airlines.c.code, airlines.c.id))
    }
    airport_ids = {
        row.code: row.id
        for row in bind.execute(sa.select(airports.c.code, airports.c.id))
    }
    existing_keys = {
        (row.flight_number, row.departure_time)
        for row in bind.execute(
            sa.select(flights.c.flight_number, flights.c.departure_time)
        )
    }

    seeded_at = datetime.utcnow()
    rows = []
    for boundary_date in sorted(boundary_dates):
        for item in generate_schedule_flights(boundary_date, boundary_date):
            key = (item["flight_number"], item["departure"])
            if key in existing_keys:
                continue
            rows.append(
                {
                    "flight_number": item["flight_number"],
                    "airline_id": airline_ids[item["airline"]],
                    "origin_id": airport_ids[item["origin"]],
                    "destination_id": airport_ids[item["destination"]],
                    "departure_time": item["departure"],
                    "arrival_time": item["departure"] + timedelta(minutes=item["duration_minutes"]),
                    "duration_minutes": item["duration_minutes"],
                    "total_seats": item["total_seats"],
                    "available_seats": item["available_seats"],
                    "base_price": item["base_price"],
                    "active": True,
                    "created_at": seeded_at,
                }
            )

    if rows:
        bind.execute(flights.insert(), rows)


def downgrade() -> None:
    # Boundary rows are retained intentionally to avoid destructive deletion
    # of schedule instances that could already be referenced by bookings.
    pass
