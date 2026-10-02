from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.airline import Airline


AIRLINES = [
    {
        "code": "A3",
        "name": "Aegean Airlines",
        "country": "Greece",
        "active": True,
    },
    {
        "code": "LH",
        "name": "Lufthansa",
        "country": "Germany",
        "active": True,
    },
    {
        "code": "AM",
        "name": "Aeromexico",
        "country": "Mexico",
        "active": True,
    },
    {
        "code": "EY",
        "name": "Etihad Airways",
        "country": "United Arab Emirates",
        "active": True,
    },
    {
        "code": "BA",
        "name": "British Airways",
        "country": "United Kingdom",
        "active": True,
    },
]


def seed_airlines() -> None:
    db = SessionLocal()

    try:
        for data in AIRLINES:
            existing = db.execute(
                select(Airline).where(Airline.code == data["code"])
            ).scalar_one_or_none()

            if existing is None:
                db.add(Airline(**data))

        db.commit()
        print("Airline seed completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_airlines()