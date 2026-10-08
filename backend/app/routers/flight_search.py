from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased
from app.core.defects import DefectType, get_active_defect
from app.db.database import get_db
from app.models.airport import Airport
from app.models.airline import Airline
from app.models.flight import Flight

router = APIRouter(prefix="/search", tags=["flight-search"])

@router.get("/flights")
async def search_flights(
    request: Request,
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    travel_date: date | None = None,
    db: Session = Depends(get_db),
):
    origin_airport = aliased(Airport)
    destination_airport = aliased(Airport)

    stmt = (
        select(Flight, Airline, origin_airport, destination_airport)
        .join(Airline, Flight.airline_id == Airline.id)
        .join(origin_airport, Flight.origin_id == origin_airport.id)
        .join(destination_airport, Flight.destination_id == destination_airport.id)
        .where(
            Flight.active.is_(True),
            origin_airport.code == origin.upper(),
            destination_airport.code == destination.upper(),
        )
        .order_by(Flight.departure_time)
    )

    if travel_date:
        # A travel date represents one calendar day, not an open-ended
        # lower-bound search. Keep historical and future schedule instances
        # independently searchable without leaking adjacent dates.
        day_start = datetime.combine(travel_date, time.min)
        day_end = day_start + timedelta(days=1)
        stmt = stmt.where(
            Flight.departure_time >= day_start,
            Flight.departure_time < day_end,
        )

    active_defect = get_active_defect(request)
    rows = db.execute(stmt).all()
    results = []
    for f, a, o, d in rows:
        seats = 999 if (active_defect and active_defect.id == DefectType.STALE_INVENTORY.value) else f.available_seats
        results.append(
            {
                "flight_id": f.id,
                "flight_number": f.flight_number,
                "airline": a.code,
                "origin": o.code,
                "destination": d.code,
                "departure_time": f.departure_time,
                "arrival_time": f.arrival_time,
                "duration_minutes": f.duration_minutes,
                "available_seats": seats,
                "base_price": float(f.base_price),
            }
        )
    return results
