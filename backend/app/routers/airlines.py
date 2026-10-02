from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.airline import Airline

router = APIRouter(prefix="/airlines", tags=["airlines"])


@router.get("")
async def list_airlines(db: Session = Depends(get_db)):
    result = db.execute(
        select(Airline).order_by(Airline.code)
    )

    airlines = result.scalars().all()

    return [
        {
            "id": airline.id,
            "code": airline.code,
            "name": airline.name,
            "country": airline.country,
            "active": airline.active,
        }
        for airline in airlines
    ]