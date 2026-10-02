import os
from contextlib import contextmanager
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db, SessionLocal
from app.main import app
from app.models.airline import Airline
from app.models.airport import Airport
from app.models.flight import Flight
from app.core.auth import DEMO_USERS, User, create_access_token
from app.db.seed import AIRLINES
from app.db.seed_airports import AIRPORTS
from app.db.seed_flights import FLIGHTS, get_id


def _create_seeded_sqlite_engine():
    """Create an in-memory SQLite engine seeded with flights, airlines, and airports."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSession() as db:
        for a in AIRLINES:
            db.add(Airline(**a))
        for ap in AIRPORTS:
            db.add(Airport(**ap))
        db.commit()

        for f in FLIGHTS:
            airline_id = get_id(db, Airline, f["airline"])
            origin_id = get_id(db, Airport, f["origin"])
            dest_id = get_id(db, Airport, f["destination"])
            arrival = f["departure"] + timedelta(minutes=f["duration_minutes"])
            db.add(
                Flight(
                    flight_number=f["flight_number"],
                    airline_id=airline_id,
                    origin_id=origin_id,
                    destination_id=dest_id,
                    departure_time=f["departure"],
                    arrival_time=arrival,
                    duration_minutes=f["duration_minutes"],
                    total_seats=f["total_seats"],
                    available_seats=f["available_seats"],
                    base_price=f["base_price"],
                    active=True,
                )
            )
        db.commit()

    return engine, TestingSession


def auth_headers(email: str = "passenger@qahub.io") -> dict[str, str]:
    record = DEMO_USERS[email]
    token = create_access_token(User(**{key: record[key] for key in ("id", "email", "name", "role")}))
    return {"Authorization": f"Bearer {token}"}


def auth_headers_for_user(user: User) -> dict[str, str]:
    """Issue a signed test identity without adding a production/demo account."""
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@contextmanager
def authenticated(client, email: str = "passenger@qahub.io"):
    original = client.headers.get("Authorization")
    client.headers["Authorization"] = auth_headers(email)["Authorization"]
    try:
        yield
    finally:
        if original is None:
            client.headers.pop("Authorization", None)
        else:
            client.headers["Authorization"] = original


@contextmanager
def authenticated_as(client, user: User):
    """Temporarily authenticate a test request as a synthetic identity."""
    original = client.headers.get("Authorization")
    client.headers["Authorization"] = auth_headers_for_user(user)["Authorization"]
    try:
        yield
    finally:
        if original is None:
            client.headers.pop("Authorization", None)
        else:
            client.headers["Authorization"] = original


# Create session-scoped SQLite fallback engine for offline testing
_offline_engine, _offline_session_factory = _create_seeded_sqlite_engine()


def _get_offline_db():
    db = _offline_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def ensure_offline_ai_provider(monkeypatch):
    """Guarantees tests execute hermetically using mock AI provider."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    yield


@pytest.fixture(autouse=True)
def ensure_db_override():
    """Autouse fixture guaranteeing get_db override remains active for all tests when offline."""
    if "DATABASE_URL" not in os.environ:
        app.dependency_overrides[get_db] = _get_offline_db
    yield


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient with automatic offline SQLite fallback when PostgreSQL is not configured."""
    if "DATABASE_URL" not in os.environ:
        app.dependency_overrides[get_db] = _get_offline_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    """Database session fixture routing to seeded SQLite offline, or PostgreSQL in CI."""
    if "DATABASE_URL" not in os.environ:
        db = _offline_session_factory()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
