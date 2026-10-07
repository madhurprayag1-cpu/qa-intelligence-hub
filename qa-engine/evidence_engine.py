"""Structured Test Evidence Persistence & Validation Engine.

Adheres strictly to MASTER PROMPT Section 13, AGENTS.md Sections 2, 5, 6, 22:
- Generates and persists structured, machine-readable evidence for every test execution.
- Captures mandatory fields:
    - test_id
    - domain
    - feature
    - layer
    - status
    - expected
    - actual
    - duration
    - environment
    - timestamp
    - agent
    - evidence
    - failure_reason
    - defect_id
    - commit_sha
- Exports run telemetry to .qa/evidence/
- Integrates seamlessly with Test Explorer and Release Quality Gate
"""

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVIDENCE_DIR = _REPO_ROOT / ".qa" / "evidence"


@dataclass
class TestEvidenceRecord:
    test_id: str
    domain: str
    feature: str
    layer: str
    status: str  # "PASS" | "FAIL" | "SKIPPED"
    expected: str
    actual: str
    duration: float
    environment: str
    timestamp: str
    agent: str
    evidence: str
    failure_reason: Optional[str] = None
    defect_id: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class EvidenceRunSummary:
    run_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    pass_rate: float
    total_duration_sec: float
    timestamp: str
    environment: str
    commit_sha: str
    records: List[TestEvidenceRecord] = field(default_factory=list)


def get_current_git_sha() -> str:
    """Retrieves current Git commit SHA safely."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL
        )
        return out.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


class EvidenceEngine:
    def __init__(self, evidence_dir: Optional[Path] = None):
        self.evidence_dir = evidence_dir or _EVIDENCE_DIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def parse_junit_xml(
        self, xml_path: Path, agent: str = "TestExecutionAgent"
    ) -> List[TestEvidenceRecord]:
        """Parses a pytest JUnit XML report into structured TestEvidenceRecords."""
        if not xml_path.exists():
            return []

        records: List[TestEvidenceRecord] = []
        commit_sha = get_current_git_sha()
        now_ts = datetime.now(timezone.utc).isoformat()

        tree = ET.parse(xml_path)
        root = tree.getroot()

        for testcase in root.iter("testcase"):
            classname = testcase.get("classname", "")
            name = testcase.get("name", "")
            duration = float(testcase.get("time", "0.0"))

            # Determine domain
            if "healthcare" in classname:
                domain = "healthcare"
            elif "fintech" in classname:
                domain = "fintech"
            elif "ecommerce" in classname:
                domain = "ecommerce"
            elif "telecom" in classname:
                domain = "telecom"
            elif any(d in classname for d in ["airlines", "airports", "bookings", "flights", "payments", "cancellation", "ancillaries"]):
                domain = "airline"
            else:
                domain = "platform"

            # Determine layer
            if "api" in classname:
                layer = "API"
            elif "database" in classname:
                layer = "DATABASE"
            elif "contract" in classname:
                layer = "CONTRACT"
            elif "security" in classname:
                layer = "SECURITY"
            elif "performance" in classname:
                layer = "PERFORMANCE"
            elif "ai" in classname:
                layer = "AI_RAG"
            elif "agents" in classname:
                layer = "AGENTS"
            elif "domains" in classname:
                layer = "DOMAIN_PACK"
            elif "regression" in classname:
                layer = "REGRESSION"
            else:
                layer = "UNIT"

            # Determine defect ID if applicable
            defect_id = None
            for part in name.split("_"):
                if part.upper().startswith("DEF"):
                    defect_id = part.upper()
                    break

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                status = "FAIL"
                actual = "AssertionError: " + (failure.get("message") or failure.text or "Assertion failed")[:200]
                failure_reason = failure.text or failure.get("message")
            elif error is not None:
                status = "FAIL"
                actual = "Error: " + (error.get("message") or error.text or "Execution error")[:200]
                failure_reason = error.text or error.get("message")
            elif skipped is not None:
                status = "SKIPPED"
                actual = "Test skipped"
                failure_reason = skipped.get("message")
            else:
                status = "PASS"
                actual = "Test passed with exit status 0"
                failure_reason = None

            records.append(
                TestEvidenceRecord(
                    test_id=f"{classname}::{name}",
                    domain=domain,
                    feature=name.replace("test_", "").replace("_", " ").title(),
                    layer=layer,
                    status=status,
                    expected="Test assertions pass without exception",
                    actual=actual,
                    duration=duration,
                    environment="local_test",
                    timestamp=now_ts,
                    agent=agent,
                    evidence=f"JUnit XML testcase: {classname}.{name} (duration: {duration:.3f}s)",
                    failure_reason=failure_reason,
                    defect_id=defect_id,
                    commit_sha=commit_sha
                )
            )

        return records

    def parse_playwright_json(
        self, json_path: Path, agent: str = "UIAutomationAgent"
    ) -> List[TestEvidenceRecord]:
        """Parses Playwright JSON report into structured TestEvidenceRecords."""
        if not json_path.exists():
            return []

        records: List[TestEvidenceRecord] = []
        commit_sha = get_current_git_sha()
        now_ts = datetime.now(timezone.utc).isoformat()

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        suites = data.get("suites", [])
        
        def traverse_suite(suite: dict, current_file: str = ""):
            file_name = suite.get("file", current_file)
            for spec in suite.get("specs", []):
                title = spec.get("title", "Unknown Playwright Spec")
                tests = spec.get("tests", [])
                for t in tests:
                    results = t.get("results", [])
                    res = results[0] if results else {}
                    status_raw = res.get("status", "passed")
                    status = "PASS" if status_raw in ["passed", "expected"] else "FAIL"
                    duration_ms = res.get("duration", 0)
                    duration_sec = duration_ms / 1000.0

                    if "booking" in file_name:
                        domain = "airline"
                    elif "healthcare" in file_name:
                        domain = "healthcare"
                    elif "fintech" in file_name:
                        domain = "fintech"
                    elif "ecommerce" in file_name:
                        domain = "ecommerce"
                    elif "telecom" in file_name:
                        domain = "telecom"
                    else:
                        domain = "platform"

                    error_msg = None
                    if status == "FAIL":
                        error_obj = res.get("error", {})
                        error_msg = error_obj.get("message") or "Playwright expectation failed"

                    records.append(
                        TestEvidenceRecord(
                            test_id=f"PW::{file_name}::{title}",
                            domain=domain,
                            feature=title,
                            layer="UI_E2E",
                            status=status,
                            expected="DOM elements resolve and user journey completes with zero UI errors",
                            actual="E2E journey completed successfully" if status == "PASS" else f"UI Failure: {error_msg[:200]}",
                            duration=duration_sec,
                            environment="local_e2e_chromium",
                            timestamp=now_ts,
                            agent=agent,
                            evidence=f"Playwright Chromium Execution for spec: {file_name} (duration: {duration_sec:.2f}s)",
                            failure_reason=error_msg,
                            defect_id=None,
                            commit_sha=commit_sha
                        )
                    )

            for child in suite.get("suites", []):
                traverse_suite(child, file_name)

        for s in suites:
            traverse_suite(s)

        return records

    def save_run_summary(
        self, records: List[TestEvidenceRecord], run_id: Optional[str] = None
    ) -> EvidenceRunSummary:
        """Saves a unified execution run summary to the evidence repository."""
        rid = run_id or f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        total = len(records)
        passed = sum(1 for r in records if r.status == "PASS")
        failed = sum(1 for r in records if r.status == "FAIL")
        skipped = sum(1 for r in records if r.status == "SKIPPED")
        pass_rate = round((passed / total * 100.0), 2) if total > 0 else 0.0
        duration_total = sum(r.duration for r in records)

        summary = EvidenceRunSummary(
            run_id=rid,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            pass_rate=pass_rate,
            total_duration_sec=round(duration_total, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="local_hermetic",
            commit_sha=get_current_git_sha(),
            records=records
        )

        run_file = self.evidence_dir / f"{rid}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)

        # Update latest_evidence.json
        latest_file = self.evidence_dir / "latest_evidence.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)

        return summary

    def get_latest_evidence(self) -> Optional[EvidenceRunSummary]:
        """Retrieves the latest verified execution evidence run."""
        latest_file = self.evidence_dir / "latest_evidence.json"
        if not latest_file.exists():
            return None
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = [TestEvidenceRecord(**r) for r in data.get("records", [])]
            data["records"] = records
            return EvidenceRunSummary(**data)
        except Exception:
            return None


if __name__ == "__main__":
    engine = EvidenceEngine()
    print(f"EvidenceEngine initialized at {engine.evidence_dir}")
