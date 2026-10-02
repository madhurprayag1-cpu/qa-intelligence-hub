import secrets
from datetime import datetime
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import User, require_roles
from app.db.database import get_db
from app.models.quality_gate_run import QualityGateRunModel

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT / "qa-engine") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "qa-engine"))

from quality_gate import (
    PRESET_POLICIES,
    QualityGateInput,
    QualityGatePolicy,
    evaluate_policy_gate,
)

router = APIRouter(prefix="/quality-gate", tags=["quality-gate"])


class QualityPolicySchema(BaseModel):
    name: str = "PRODUCTION_STRICT"
    min_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    max_failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    max_critical_defects: int = Field(default=0, ge=0)
    min_rag_groundedness: float = Field(default=0.85, ge=0.0, le=1.0)
    min_rag_context_relevance: float = Field(default=0.80, ge=0.0, le=1.0)
    min_rag_citation_accuracy: float = Field(default=0.85, ge=0.0, le=1.0)
    min_rag_truthful_refusal: float = Field(default=0.90, ge=0.0, le=1.0)
    max_contract_failures: int = Field(default=0, ge=0)
    max_security_vulnerabilities: int = Field(default=0, ge=0)
    max_critical_security_vulnerabilities: int = Field(default=0, ge=0)
    max_pci_dss_violations: int = Field(default=0, ge=0)
    min_security_compliance_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    max_flaky_tests: int = Field(default=0, ge=0)
    min_total_tests: int = Field(default=1, ge=0)


class EvaluateQualityGateRequest(BaseModel):
    policy_name: Optional[str] = "PRODUCTION_STRICT"
    custom_policy: Optional[QualityPolicySchema] = None
    total_tests: int = Field(default=0, ge=0)
    passed_tests: int = Field(default=0, ge=0)
    failed_tests: int = Field(default=0, ge=0)
    skipped_tests: int = Field(default=0, ge=0)
    critical_defects: int = Field(default=0, ge=0)
    contract_failures: int = Field(default=0, ge=0)
    security_vulnerabilities: int = Field(default=0, ge=0)
    critical_security_vulnerabilities: int = Field(default=0, ge=0)
    pci_dss_violations: int = Field(default=0, ge=0)
    security_compliance_rate: Optional[float] = None
    security_findings: Optional[List[Dict[str, Any]]] = None
    rag_groundedness_score: Optional[float] = None
    rag_context_relevance_score: Optional[float] = None
    rag_citation_accuracy_score: Optional[float] = None
    rag_truthful_refusal_score: Optional[float] = None
    flaky_tests: int = Field(default=0, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class QualityGateResponse(BaseModel):
    run_id: Optional[str] = None
    passed: bool
    status: str
    policy_name: str
    pass_rate: float
    failure_rate: float
    total: int
    passed_tests: int
    failed_tests: int
    skipped: int
    violations: List[str]
    signals: Dict[str, Any]
    evaluated_at: str


@router.get("/policies", response_model=Dict[str, QualityPolicySchema])
async def get_policies():
    """Retrieve all standard preset Quality Gate policies."""
    return {
        key: QualityPolicySchema(
            name=p.name,
            min_pass_rate=p.min_pass_rate,
            max_failure_rate=p.max_failure_rate,
            max_critical_defects=p.max_critical_defects,
            min_rag_groundedness=p.min_rag_groundedness,
            min_rag_context_relevance=p.min_rag_context_relevance,
            min_rag_citation_accuracy=p.min_rag_citation_accuracy,
            min_rag_truthful_refusal=p.min_rag_truthful_refusal,
            max_contract_failures=p.max_contract_failures,
            max_security_vulnerabilities=p.max_security_vulnerabilities,
            max_critical_security_vulnerabilities=p.max_critical_security_vulnerabilities,
            max_pci_dss_violations=p.max_pci_dss_violations,
            min_security_compliance_rate=p.min_security_compliance_rate,
            max_flaky_tests=p.max_flaky_tests,
            min_total_tests=p.min_total_tests,
        )
        for key, p in PRESET_POLICIES.items()
    }


@router.post("/evaluate", response_model=QualityGateResponse)
async def evaluate_gate_endpoint(
    payload: EvaluateQualityGateRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluate release quality gate against specified policy and test execution signals.
    Persists evaluation audit trail into PostgreSQL for historical trend tracking.
    """
    policy: QualityGatePolicy
    if payload.custom_policy:
        c = payload.custom_policy
        policy = QualityGatePolicy(
            name=c.name,
            min_pass_rate=c.min_pass_rate,
            max_failure_rate=c.max_failure_rate,
            max_critical_defects=c.max_critical_defects,
            min_rag_groundedness=c.min_rag_groundedness,
            min_rag_context_relevance=c.min_rag_context_relevance,
            min_rag_citation_accuracy=c.min_rag_citation_accuracy,
            min_rag_truthful_refusal=c.min_rag_truthful_refusal,
            max_contract_failures=c.max_contract_failures,
            max_security_vulnerabilities=c.max_security_vulnerabilities,
            max_critical_security_vulnerabilities=c.max_critical_security_vulnerabilities,
            max_pci_dss_violations=c.max_pci_dss_violations,
            min_security_compliance_rate=c.min_security_compliance_rate,
            max_flaky_tests=c.max_flaky_tests,
            min_total_tests=c.min_total_tests,
        )
    elif payload.policy_name in PRESET_POLICIES:
        policy = PRESET_POLICIES[payload.policy_name]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown policy '{payload.policy_name}'. Available: {list(PRESET_POLICIES.keys())}",
        )

    gate_input = QualityGateInput(
        total_tests=payload.total_tests,
        passed_tests=payload.passed_tests,
        failed_tests=payload.failed_tests,
        skipped_tests=payload.skipped_tests,
        critical_defects=payload.critical_defects,
        contract_failures=payload.contract_failures,
        security_vulnerabilities=payload.security_vulnerabilities,
        critical_security_vulnerabilities=payload.critical_security_vulnerabilities,
        pci_dss_violations=payload.pci_dss_violations,
        security_compliance_rate=payload.security_compliance_rate,
        security_findings=payload.security_findings or [],
        rag_groundedness_score=payload.rag_groundedness_score,
        rag_context_relevance_score=payload.rag_context_relevance_score,
        rag_citation_accuracy_score=payload.rag_citation_accuracy_score,
        rag_truthful_refusal_score=payload.rag_truthful_refusal_score,
        flaky_tests=payload.flaky_tests,
        metadata=payload.metadata or {},
    )

    res = evaluate_policy_gate(gate_input, policy)
    run_id = f"QG-RUN-{secrets.token_hex(4).upper()}"

    # Persist audit log to database if session is active
    if db is not None:
        try:
            record = QualityGateRunModel(
                run_id=run_id,
                policy_name=res.policy_name,
                passed=res.passed,
                status=res.status,
                pass_rate=res.pass_rate,
                failure_rate=res.failure_rate,
                total_tests=res.total,
                passed_tests=res.passed_tests,
                failed_tests=res.failed_tests,
                skipped_tests=res.skipped,
                critical_defects=payload.critical_defects,
                contract_failures=payload.contract_failures,
                security_vulnerabilities=payload.security_vulnerabilities,
                rag_groundedness_score=payload.rag_groundedness_score,
                violations=res.violations,
                signals=res.signals,
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()

    return QualityGateResponse(
        run_id=run_id,
        passed=res.passed,
        status=res.status,
        policy_name=res.policy_name,
        pass_rate=res.pass_rate,
        failure_rate=res.failure_rate,
        total=res.total,
        passed_tests=res.passed_tests,
        failed_tests=res.failed_tests,
        skipped=res.skipped,
        violations=res.violations,
        signals=res.signals,
        evaluated_at=res.evaluated_at,
    )


@router.get("/runs", response_model=List[QualityGateResponse])
async def list_quality_gate_runs(
    limit: int = 20,
    policy: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve historical quality gate execution runs and audit telemetry."""
    query = select(QualityGateRunModel).order_by(QualityGateRunModel.created_at.desc()).limit(limit)
    if policy:
        query = query.where(QualityGateRunModel.policy_name == policy)
    try:
        runs = db.execute(query).scalars().all()
        return [
            QualityGateResponse(
                run_id=r.run_id,
                passed=r.passed,
                status=r.status,
                policy_name=r.policy_name,
                pass_rate=r.pass_rate,
                failure_rate=r.failure_rate,
                total=r.total_tests,
                passed_tests=r.passed_tests,
                failed_tests=r.failed_tests,
                skipped=r.skipped_tests,
                violations=r.violations or [],
                signals=r.signals or {},
                evaluated_at=r.created_at.isoformat(),
            )
            for r in runs
        ]
    except Exception:
        return []


@router.get("/runs/{run_id}", response_model=QualityGateResponse)
async def get_quality_gate_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Fetch audit telemetry for a specific historical quality gate execution."""
    try:
        record = db.execute(
            select(QualityGateRunModel).where(QualityGateRunModel.run_id == run_id)
        ).scalar_one_or_none()
    except Exception:
        record = None

    if not record:
        raise HTTPException(status_code=404, detail=f"Quality gate run '{run_id}' not found")

    return QualityGateResponse(
        run_id=record.run_id,
        passed=record.passed,
        status=record.status,
        policy_name=record.policy_name,
        pass_rate=record.pass_rate,
        failure_rate=record.failure_rate,
        total=record.total_tests,
        passed_tests=record.passed_tests,
        failed_tests=record.failed_tests,
        skipped=record.skipped_tests,
        violations=record.violations or [],
        signals=record.signals or {},
        evaluated_at=record.created_at.isoformat(),
    )



class OverrideQualityGateRequest(BaseModel):
    override_reason: str = Field(min_length=5, max_length=255)
    target_release: str = "v1.0.0"
    approver_notes: Optional[str] = None


class QualityGateOverrideResponse(BaseModel):
    approved: bool
    override_by: str
    override_role: str
    target_release: str
    reason: str
    audit_timestamp: str


@router.post("/override", response_model=QualityGateOverrideResponse)
async def override_quality_gate(
    payload: OverrideQualityGateRequest,
    current_user: User = Depends(require_roles(["release_manager", "admin"])),
):
    """Allows authorized Release Managers or Admins to sign off an emergency quality gate override."""
    return QualityGateOverrideResponse(
        approved=True,
        override_by=current_user.email,
        override_role=current_user.role,
        target_release=payload.target_release,
        reason=payload.override_reason,
        audit_timestamp=datetime.utcnow().isoformat(),
    )
