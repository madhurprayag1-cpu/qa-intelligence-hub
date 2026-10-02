"""Database initialization and seeding runner."""

import logging
from app.db.seed import seed_airlines
from app.db.seed_airports import seed_airports
from app.db.seed_flights import seed_flights

logger = logging.getLogger("app.db.init_db")


def seed_all() -> None:
    """Seeds airlines, airports, and flights in sequential dependency order."""
    print("--> Seeding airlines...")
    seed_airlines()
    print("--> Seeding airports...")
    seed_airports()
    print("--> Seeding flights...")
    seed_flights()
    print("--> All database seed data initialized successfully.")


if __name__ == "__main__":
    seed_all()
