from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.airport import Airport


AIRPORTS = [
    {
        "code": "ATH",
        "name": "Athens International Airport",
        "city": "Athens",
        "country": "Greece",
        "timezone": "Europe/Athens",
        "active": True,
    },
    {
        "code": "SKG",
        "name": "Thessaloniki Airport",
        "city": "Thessaloniki",
        "country": "Greece",
        "timezone": "Europe/Athens",
        "active": True,
    },
    {
        "code": "LHR",
        "name": "Heathrow Airport",
        "city": "London",
        "country": "United Kingdom",
        "timezone": "Europe/London",
        "active": True,
    },
    {
        "code": "FRA",
        "name": "Frankfurt Airport",
        "city": "Frankfurt",
        "country": "Germany",
        "timezone": "Europe/Berlin",
        "active": True,
    },
    {
        "code": "CDG",
        "name": "Charles de Gaulle Airport",
        "city": "Paris",
        "country": "France",
        "timezone": "Europe/Paris",
        "active": True,
    },
    {
        "code": "AMS",
        "name": "Amsterdam Airport Schiphol",
        "city": "Amsterdam",
        "country": "Netherlands",
        "timezone": "Europe/Amsterdam",
        "active": True,
    },
    {
        "code": "AUH",
        "name": "Zayed International Airport",
        "city": "Abu Dhabi",
        "country": "United Arab Emirates",
        "timezone": "Asia/Dubai",
        "active": True,
    },
    {
        "code": "DXB",
        "name": "Dubai International Airport",
        "city": "Dubai",
        "country": "United Arab Emirates",
        "timezone": "Asia/Dubai",
        "active": True,
    },
    {
        "code": "JFK",
        "name": "John F. Kennedy International Airport",
        "city": "New York",
        "country": "United States",
        "timezone": "America/New_York",
        "active": True,
    },
    {
        "code": "ORD",
        "name": "Chicago O'Hare International Airport",
        "city": "Chicago",
        "country": "United States",
        "timezone": "America/Chicago",
        "active": True,
    },
    {
        "code": "BOM",
        "name": "Chhatrapati Shivaji Maharaj International Airport",
        "city": "Mumbai",
        "country": "India",
        "timezone": "Asia/Kolkata",
        "active": True,
    },
    {
        "code": "DEL",
        "name": "Indira Gandhi International Airport",
        "city": "Delhi",
        "country": "India",
        "timezone": "Asia/Kolkata",
        "active": True,
    },
]


def seed_airports() -> None:
    db = SessionLocal()

    try:
        for data in AIRPORTS:
            existing = db.execute(
                select(Airport).where(Airport.code == data["code"])
            ).scalar_one_or_none()

            if existing is None:
                db.add(Airport(**data))

        db.commit()
        print("Airport seed completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_airports()