from datetime import datetime
from typing import Any, List
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class HealthcarePatientModel(Base):
    """Persistent storage for HL7 FHIR Release 4 Patient resources."""
    __tablename__ = "healthcare_patients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # MRN
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    family_name: Mapped[str] = mapped_column(String(100), nullable=False)
    given_names: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    ssn_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_masked: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HealthcareObservationModel(Base):
    """Persistent storage for HL7 FHIR Release 4 Clinical Observations (vital signs & labs)."""
    __tablename__ = "healthcare_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("healthcare_patients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    loinc_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_quantity: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="final")
    effective_date_time: Mapped[str] = mapped_column(String(50), nullable=False)  # ISO 8601
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HealthcareAppointmentModel(Base):
    """Persistent storage for HL7 FHIR Release 4 Appointments."""
    __tablename__ = "healthcare_appointments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("healthcare_patients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    practitioner_ref: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_time: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    end_time: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="booked", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
