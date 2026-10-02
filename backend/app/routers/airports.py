from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.airport import Airport

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("")
async def list_airports(db: Session = Depends(get_db)):
    result = db.execute(
        select(Airport).order_by(Airport.code)
    )

    airports = result.scalars().all()

    return [
        {
            "id": airport.id,
            "code": airport.code,
            "name": airport.name,
            "city": airport.city,
            "country": airport.country,
            "timezone": airport.timezone,
            "active": airport.active,
        }
        for airport in airports
    ]