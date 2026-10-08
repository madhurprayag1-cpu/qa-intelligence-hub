"""extend synthetic flight schedule coverage across a rolling five-year window

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-10-08 00:00:00.000000
"""

from datetime import date, datetime, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.seed import AIRLINES
from app.db.seed_airports import AIRPORTS
from app.db.seed_flights import generate_schedule_flights


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    flights = sa.Table("flights", metadata, autoload_with=bind)
    airlines = sa.Table("airlines", metadata, autoload_with=bind)
    airports = sa.Table("airports", metadata, autoload_with=bind)

    # Keep two years of historical schedule data and three years of future
    # schedule data relative to the deployment/migration date.
    today = date.today()
    start_date = today.replace(year=today.year - 2)
    end_date = today.replace(year=today.year + 3)

    # CI applies Alembic before the normal seed runner, while production
    # databases may already contain these reference rows. Make the migration
    # self-contained and idempotent for the flight schedule data it introduces.
    seeded_at = datetime.utcnow()
    existing_airlines = {
        row.code
        for row in bind.execute(sa.select(airlines.c.code))
    }
    missing_airlines = [
        {**item, "created_at": seeded_at}
        for item in AIRLINES
        if item["code"] not in existing_airlines
    ]
    if missing_airlines:
        bind.execute(airlines.insert(), missing_airlines)

    existing_airports = {
        row.code
        for row in bind.execute(sa.select(airports.c.code))
    }
    missing_airports = [
        {**item, "created_at": seeded_at}
        for item in AIRPORTS
        if item["code"] not in existing_airports
    ]
    if missing_airports:
        bind.execute(airports.insert(), missing_airports)

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
    for item in generate_schedule_flights(start_date, end_date):
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

    # Chunk inserts so the migration remains safe for PostgreSQL parameter
    # limits while still loading tens of thousands of deterministic instances.
    for offset in range(0, len(rows), 1000):
        bind.execute(flights.insert(), rows[offset : offset + 1000])

    # Search is always constrained by route + calendar-day range. This
    # composite index keeps long-range date searches efficient.
    op.create_index(
        "ix_flights_route_departure",
        "flights",
        ["origin_id", "destination_id", "departure_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_flights_route_departure", table_name="flights")
    # Flight schedule rows are intentionally retained on downgrade to avoid
    # destructive deletion of data that may already be referenced by bookings.
