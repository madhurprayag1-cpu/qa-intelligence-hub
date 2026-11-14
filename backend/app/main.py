from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.observability import ObservabilityMiddleware
from app.core.production_safety import ProductionSafetyMiddleware, is_production_runtime
from app.db.database import engine
from app.models.lifecycle import ensure_lifecycle_tables
from app.routers import (
    ai,
    airlines,
    airports,
    auth,
    bookings,
    defects,
    flight_search,
    flights,
    health,
    healthcare,
    ecommerce,
    fintech,
    payments,
    qa,
    quality_gate,
    telecom,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for the QA Intelligence Hub platform.",
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(ProductionSafetyMiddleware)
app.add_middleware(
    CORSMiddleware,
    # Exact origins only. The previous *.vercel.app regex trusted arbitrary
    # preview projects and user-controlled Vercel subdomains.
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(airlines.router)
app.include_router(airports.router)
app.include_router(flights.router)
app.include_router(flight_search.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(ai.router)
app.include_router(defects.router)
app.include_router(quality_gate.router)
app.include_router(qa.router)
app.include_router(healthcare.router)
app.include_router(fintech.router)
app.include_router(ecommerce.router)
app.include_router(telecom.router)


@app.on_event("startup")
async def ensure_additive_lifecycle_schema() -> None:
    # Never run DDL during Vercel Preview or Production cold starts. Preview
    # DATABASE_URL values may point at shared data; migrations belong in the
    # isolated CI/deployment migration workflow, not request-serving startup.
    if not is_production_runtime():
        ensure_lifecycle_tables(engine)
