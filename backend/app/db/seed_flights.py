from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.airline import Airline
from app.models.airport import Airport
from app.models.flight import Flight


FLIGHTS = [
    {
        "flight_number": "A3101",
        "airline": "A3",
        "origin": "ATH",
        "destination": "SKG",
        "departure": datetime(2026, 10, 15, 9, 0),
        "duration_minutes": 55,
        "total_seats": 180,
        "available_seats": 142,
        "base_price": 89.00,
    },
    {
        "flight_number": "A3102",
        "airline": "A3",
        "origin": "SKG",
        "destination": "ATH",
        "departure": datetime(2026, 10, 15, 12, 0),
        "duration_minutes": 55,
        "total_seats": 180,
        "available_seats": 156,
        "base_price": 89.00,
    },
    {
        "flight_number": "A3205",
        "airline": "A3",
        "origin": "ATH",
        "destination": "LHR",
        "departure": datetime(2026, 10, 15, 10, 30),
        "duration_minutes": 245,
        "total_seats": 210,
        "available_seats": 174,
        "base_price": 249.00,
    },
    {
        "flight_number": "LH441",
        "airline": "LH",
        "origin": "FRA",
        "destination": "LHR",
        "departure": datetime(2026, 10, 15, 8, 15),
        "duration_minutes": 95,
        "total_seats": 200,
        "available_seats": 121,
        "base_price": 159.00,
    },
    {
        "flight_number": "LH442",
        "airline": "LH",
        "origin": "LHR",
        "destination": "FRA",
        "departure": datetime(2026, 10, 15, 14, 30),
        "duration_minutes": 95,
        "total_seats": 200,
        "available_seats": 98,
        "base_price": 159.00,
    },
    {
        "flight_number": "LH760",
        "airline": "LH",
        "origin": "FRA",
        "destination": "DEL",
        "departure": datetime(2026, 10, 15, 13, 0),
        "duration_minutes": 470,
        "total_seats": 280,
        "available_seats": 213,
        "base_price": 599.00,
    },
    {
        "flight_number": "EY201",
        "airline": "EY",
        "origin": "AUH",
        "destination": "LHR",
        "departure": datetime(2026, 10, 15, 9, 45),
        "duration_minutes": 440,
        "total_seats": 280,
        "available_seats": 189,
        "base_price": 529.00,
    },
    {
        "flight_number": "EY202",
        "airline": "EY",
        "origin": "LHR",
        "destination": "AUH",
        "departure": datetime(2026, 10, 15, 20, 0),
        "duration_minutes": 415,
        "total_seats": 280,
        "available_seats": 165,
        "base_price": 529.00,
    },
    {
        "flight_number": "AM400",
        "airline": "AM",
        "origin": "JFK",
        "destination": "ORD",
        "departure": datetime(2026, 10, 15, 11, 0),
        "duration_minutes": 165,
        "total_seats": 160,
        "available_seats": 117,
        "base_price": 189.00,
    },
    {
        "flight_number": "BA178",
        "airline": "BA",
        "origin": "LHR",
        "destination": "JFK",
        "departure": datetime(2026, 10, 15, 16, 30),
        "duration_minutes": 450,
        "total_seats": 300,
        "available_seats": 226,
        "base_price": 649.00,
    },
    {
        "flight_number": "BA179",
        "airline": "BA",
        "origin": "JFK",
        "destination": "LHR",
        "departure": datetime(2026, 10, 15, 21, 15),
        "duration_minutes": 425,
        "total_seats": 300,
        "available_seats": 204,
        "base_price": 649.00,
    },
    {
        "flight_number": "A3990",
        "airline": "A3",
        "origin": "ATH",
        "destination": "CDG",
        "departure": datetime(2026, 10, 16, 7, 30),
        "duration_minutes": 195,
        "total_seats": 180,
        "available_seats": 133,
        "base_price": 199.00,
    },
]


def get_id(db, model, code: str) -> int:
    record = db.execute(
        select(model).where(model.code == code)
    ).scalar_one()

    return record.id


def seed_flights() -> None:
    db = SessionLocal()

    try:
        for data in FLIGHTS:
            airline_id = get_id(db, Airline, data["airline"])
            origin_id = get_id(db, Airport, data["origin"])
            destination_id = get_id(db, Airport, data["destination"])

            existing = db.execute(
                select(Flight).where(
                    Flight.flight_number == data["flight_number"]
                )
            ).scalar_one_or_none()

            if existing is None:
                arrival = data["departure"] + timedelta(
                    minutes=data["duration_minutes"]
                )

                db.add(
                    Flight(
                        flight_number=data["flight_number"],
                        airline_id=airline_id,
                        origin_id=origin_id,
                        destination_id=destination_id,
                        departure_time=data["departure"],
                        arrival_time=arrival,
                        duration_minutes=data["duration_minutes"],
                        total_seats=data["total_seats"],
                        available_seats=data["available_seats"],
                        base_price=data["base_price"],
                        active=True,
                    )
                )
            else:
                existing.available_seats = data["available_seats"]
                existing.total_seats = data["total_seats"]
                existing.active = True

        db.commit()
        print("Flight seed completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_flights()