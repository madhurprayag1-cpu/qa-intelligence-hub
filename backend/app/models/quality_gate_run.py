from datetime import datetime
from typing import Any, List
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class QualityGateRunModel(Base):
    """Persistent storage for release quality gate execution telemetry and audit history."""

    __tablename__ = "quality_gate_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(64), index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="FAILED")
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0)
    skipped_tests: Mapped[int] = mapped_column(Integer, default=0)
    critical_defects: Mapped[int] = mapped_column(Integer, default=0)
    contract_failures: Mapped[int] = mapped_column(Integer, default=0)
    security_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    rag_groundedness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    violations: Mapped[List[str]] = mapped_column(JSON, default=list)
    signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
