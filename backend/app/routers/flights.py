from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.db.database import get_db
from app.models.airline import Airline
from app.models.airport import Airport
from app.models.flight import Flight

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/search")
async def search_flights_alias(
    request: Request,
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    travel_date: date | None = None,
    db: Session = Depends(get_db),
):
    from app.routers.flight_search import search_flights
    return await search_flights(request, origin, destination, travel_date, db)


@router.get("")
async def list_flights(db: Session = Depends(get_db)):
    origin = aliased(Airport)
    destination = aliased(Airport)

    statement = (
        select(Flight, Airline, origin, destination)
        .join(Airline, Flight.airline_id == Airline.id)
        .join(origin, Flight.origin_id == origin.id)
        .join(destination, Flight.destination_id == destination.id)
        .where(Flight.active.is_(True))
        .order_by(Flight.departure_time)
    )

    results = db.execute(statement).all()

    return [
        {
            "id": flight.id,
            "flight_number": flight.flight_number,
            "airline": {
                "code": airline.code,
                "name": airline.name,
            },
            "origin": {
                "code": origin_airport.code,
                "name": origin_airport.name,
                "city": origin_airport.city,
            },
            "destination": {
                "code": destination_airport.code,
                "name": destination_airport.name,
                "city": destination_airport.city,
            },
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time,
            "duration_minutes": flight.duration_minutes,
            "total_seats": flight.total_seats,
            "available_seats": flight.available_seats,
            "base_price": float(flight.base_price),
            "active": flight.active,
        }
        for flight, airline, origin_airport, destination_airport in results
    ]