from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class RequirementTraceModel(Base):
    """Durable requirement -> acceptance criteria -> test traceability record."""

    __tablename__ = "requirement_traces"

    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    requirement: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(40), index=True, default="cross-domain")
    impacted_components: Mapped[list[str]] = mapped_column(JSON, default=list)
    acceptance_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    test_scenarios: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    engineering_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="READY_FOR_IMPLEMENTATION", index=True)
    source_sha: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductionObservationModel(Base):
    """Durable production observation used as input to incident/RCA workflows."""

    __tablename__ = "production_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    signal: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    serving_sha: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductionIncidentModel(Base):
    """Durable production incident and RCA record."""

    __tablename__ = "production_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="OPEN")
    summary: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_sha: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
