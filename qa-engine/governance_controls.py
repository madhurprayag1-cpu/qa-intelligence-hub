"""Shared deterministic controls for QA governance."""
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GateResult:
    passed: bool
    errors: tuple[str, ...] = ()


def validate_execution_policy(policy: Mapping[str, Any]) -> GateResult:
    errors = []
    try:
        retries = policy.get("retries", 0)
        timeout = policy.get("timeout_seconds", 60)
        workers = policy.get("workers", 1)
        if type(retries) is not int or not 0 <= retries <= 3:
            errors.append("retries must be between 0 and 3")
        if type(timeout) is not int or not 1 <= timeout <= 600:
            errors.append("timeout_seconds must be between 1 and 600")
        if type(workers) is not int or not 1 <= workers <= 32:
            errors.append("workers must be between 1 and 32")
        if policy.get("allow_production_mutations", False) is not False:
            errors.append("production mutations must remain disabled")
    except (AttributeError, TypeError):
        errors.append("policy must be a mapping")
    return GateResult(not errors, tuple(errors))


def authorize_action(action: str, environment: str, approved_by: str = "") -> GateResult:
    read_only = {"read", "inspect", "analyze", "report", "run_test", "generate_test_proposal"}
    mutating = {"write", "delete", "deploy", "migrate", "change_permissions", "apply_self_heal"}
    if environment not in {"local", "test", "staging", "production"}:
        return GateResult(False, ("unknown environment",))
    if action in read_only:
        return GateResult(True)
    if action not in mutating:
        return GateResult(False, ("unrecognized action",))
    if environment == "production":
        return GateResult(False, ("mutating production actions are prohibited",))
    if action in {"deploy", "migrate", "change_permissions", "apply_self_heal"} and not approved_by.strip():
        return GateResult(False, ("named human approval is required",))
    return GateResult(True)


def validate_test_data(data: Mapping[str, Any], environment: str) -> GateResult:
    errors = []
    if environment == "production":
        errors.append("test data cannot be generated or mutated in production")
    if data.get("synthetic") is not True:
        errors.append("synthetic=true is required")
    sensitive_parts = ("pass" + "word", "sec" + "ret", "to" + "ken", "api" + "_key", "ssn", "cvv")
    for key in data:
        if any(part in str(key).lower() for part in sensitive_parts):
            errors.append("sensitive field name is prohibited")
    if data.get("contains_real_customer_data") is True:
        errors.append("real customer data is prohibited")
    return GateResult(not errors, tuple(errors))


def validate_traceability(requirements, tests) -> GateResult:
    linked = {str(t.get("requirement_id", "")) for t in tests if t.get("enabled", True) is True}
    errors, seen = [], set()
    for req in requirements:
        if req.get("active", True) is False:
            continue
        rid = str(req.get("id", "")).strip()
        if not rid:
            errors.append("active requirement needs an id")
        elif rid in seen:
            errors.append("duplicate requirement id: " + rid)
        else:
            seen.add(rid)
            if rid not in linked:
                errors.append("requirement has no enabled test: " + rid)
    return GateResult(not errors, tuple(errors))


def validate_healing_proposal(proposal: Mapping[str, Any]) -> GateResult:
    errors = []
    if proposal.get("change_type") != "locator":
        errors.append("only locator proposals are allowed")
    confidence = proposal.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or confidence < 0.90 or confidence > 1:
        errors.append("confidence must be between 0.90 and 1")
    if str(proposal.get("domain", "")).lower() in {"auth", "security", "payments"}:
        errors.append("protected domains are excluded")
    if proposal.get("human_approved") is not True:
        errors.append("human approval is required")
    if proposal.get("auto_apply") is True:
        errors.append("proposal cannot auto-apply")
    return GateResult(not errors, tuple(errors))


def classify_failure(message: str, status_code=None) -> str:
    value = str(message).lower()
    if status_code in {401, 403} or "forbidden" in value or "unauthorized" in value:
        return "AUTHORIZATION"
    if "timeout" in value or "timed out" in value:
        return "TIMEOUT"
    if "connection refused" in value or "network unreachable" in value:
        return "INFRASTRUCTURE"
    if "assertion" in value or "expected " in value:
        return "ASSERTION"
    if "schema" in value or "contract" in value:
        return "CONTRACT"
    if "locator" in value or "element not found" in value:
        return "LOCATOR"
    return "UNKNOWN"


def coverage_gaps(requirements, tests):
    linked = {str(t.get("requirement_id", "")) for t in tests if t.get("enabled", True) is True}
    return [str(r.get("id", "<missing-id>")) for r in requirements
            if r.get("active", True) is not False and str(r.get("id", "")) not in linked]


def evaluate_definition_of_done(evidence: Mapping[str, Any]) -> GateResult:
    errors = []
    for key in ("tests_passed", "security_passed", "coverage_complete", "review_approved"):
        if evidence.get(key) is not True:
            errors.append(key + " must be true")
    tested, release = evidence.get("tested_revision"), evidence.get("release_revision")
    if not tested or tested != release:
        errors.append("tested revision must match release revision")
    if evidence.get("critical_defects", 1) != 0:
        errors.append("critical defects must be zero")
    if not evidence.get("evidence_uri"):
        errors.append("evidence reference is required")
    if evidence.get("skipped_tests", 0) != 0:
        errors.append("skipped tests must be zero")
    return GateResult(not errors, tuple(errors))
