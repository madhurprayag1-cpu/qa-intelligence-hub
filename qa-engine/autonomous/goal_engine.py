"""Persistent Goal Engine for Autonomous Closed-Loop Engineering.

Adheres strictly to MASTER PROMPT Sections 4, 5, 22:
- Persistent goal representation (.qa/goals/ and .qa/autonomous/goals/)
- Canonical GOAL-AUTO-001 definition with 20 acceptance criteria
- Decomposes goals into structured dependency TaskGraphs
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from autonomous.task_graph import TaskGraph, TaskNode


@dataclass
class GoalAcceptanceCriterion:
    id: int
    description: str
    satisfied: bool = False
    evidence_ref: Optional[str] = None
    verified_at: Optional[str] = None


@dataclass
class GoalDefinition:
    goal_id: str
    objective: str
    description: str
    priority: str  # "CRITICAL" | "HIGH" | "MEDIUM"
    scope: List[str]
    acceptance_criteria: List[GoalAcceptanceCriterion]
    constraints: List[str]
    status: str = "NOT_STARTED"  # "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "FAILED"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    current_phase: str = "INITIALIZATION"
    progress_pct: float = 0.0
    tasks: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    final_verdict: Optional[str] = None  # "PRODUCTION_READY" | "CONDITIONAL" | "NOT_READY"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalDefinition":
        ac_data = data.pop("acceptance_criteria", [])
        ac_list = [GoalAcceptanceCriterion(**ac) for ac in ac_data]
        return cls(acceptance_criteria=ac_list, **data)


class GoalEngine:
    """Manages goal persistence, lifecycle evaluation, and task decomposition."""

    def __init__(self, goals_dir: Optional[Path] = None):
        self.goals_dir = goals_dir or (_REPO_ROOT / ".qa" / "autonomous" / "goals")
        self.goals_dir.mkdir(parents=True, exist_ok=True)
        # Mirror to .qa/goals for multi-path transparency
        self.mirror_dir = _REPO_ROOT / ".qa" / "goals"
        self.mirror_dir.mkdir(parents=True, exist_ok=True)

    def save_goal(self, goal: GoalDefinition) -> None:
        goal.updated_at = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(goal.to_dict(), indent=2)

        file_primary = self.goals_dir / f"{goal.goal_id}.json"
        file_primary.write_text(serialized, encoding="utf-8")

        file_mirror = self.mirror_dir / f"{goal.goal_id}.json"
        file_mirror.write_text(serialized, encoding="utf-8")

    def load_goal(self, goal_id: str) -> Optional[GoalDefinition]:
        file_primary = self.goals_dir / f"{goal_id}.json"
        if file_primary.exists():
            data = json.loads(file_primary.read_text(encoding="utf-8"))
            return GoalDefinition.from_dict(data)
        file_mirror = self.mirror_dir / f"{goal_id}.json"
        if file_mirror.exists():
            data = json.loads(file_mirror.read_text(encoding="utf-8"))
            return GoalDefinition.from_dict(data)
        return None

    def create_goal_auto_001(self) -> GoalDefinition:
        """Instantiates canonical GOAL-AUTO-001 (MASTER PROMPT Section 22)."""
        criteria_descriptions = [
            "All advertised features audited.",
            "All five domains audited.",
            "UI functionality verified.",
            "API functionality verified.",
            "Database integrity verified.",
            "Security verified.",
            "Performance verified.",
            "AI/RAG verified.",
            "Agent functionality verified.",
            "Test inventory reconciled.",
            "Missing critical tests added.",
            "Defects automatically investigated.",
            "Safe fixes automatically implemented.",
            "Complete regression passes.",
            "CI passes.",
            "Production-safe smoke verification passes.",
            "Documentation synchronized.",
            "Evidence is complete.",
            "No unresolved critical defects.",
            "Final quality gate passes.",
        ]

        criteria = [
            GoalAcceptanceCriterion(id=idx + 1, description=desc)
            for idx, desc in enumerate(criteria_descriptions)
        ]

        goal = GoalDefinition(
            goal_id="GOAL-AUTO-001",
            objective="Complete the remaining production-readiness work for QA Intelligence Hub.",
            description=(
                "Comprehensive autonomous Quality Engineering audit, capability verification, "
                "multi-domain testing, AI/RAG quality assurance, security compliance, regression, "
                "and PRODUCTION_STRICT Quality Gate certification."
            ),
            priority="CRITICAL",
            scope=[
                "airline", "healthcare", "fintech", "ecommerce", "telecom",
                "api", "ui", "database", "security", "performance", "ai_rag",
                "agents", "governance", "documentation"
            ],
            acceptance_criteria=criteria,
            constraints=[
                "Never weaken test assertions",
                "Branch-isolated defect repairs capped at 3 attempts",
                "Zero destructive mutations to production database",
                "Provider-independent AI architecture preserved",
                "Strict adherence to PRODUCTION_STRICT fail-closed policy",
            ],
            tasks=[],
        )
        self.save_goal(goal)
        return goal

    def build_task_graph_for_goal(self, goal: GoalDefinition) -> TaskGraph:
        """Decomposes a goal into a concrete dependency TaskGraph."""
        graph = TaskGraph()

        # 1. Discovery
        graph.add_task(
            TaskNode(
                task_id="TASK-01-DISCOVER",
                name="System & Capability Discovery",
                description="Discover all test capabilities, routes, domain packs, and existing baseline.",
                agent_id="DiscoveryAgent",
                prerequisites=[],
            )
        )

        # 2. Planning
        graph.add_task(
            TaskNode(
                task_id="TASK-02-PLAN",
                name="Autonomous Execution Planning",
                description="Decompose execution scope, impact analysis, and verification batches.",
                agent_id="PlanningAgent",
                prerequisites=["TASK-01-DISCOVER"],
            )
        )

        # 3. Domain Audits (Parallelizable)
        domains = [
            ("TASK-03-DOM-AIRLINE", "Airline NDC Domain Audit", "airline"),
            ("TASK-04-DOM-HEALTHCARE", "Healthcare FHIR Domain Audit", "healthcare"),
            ("TASK-05-DOM-FINTECH", "FinTech Core Banking Domain Audit", "fintech"),
            ("TASK-06-DOM-ECOMMERCE", "E-Commerce Retail Domain Audit", "ecommerce"),
            ("TASK-07-DOM-TELECOM", "Telecom 5G/BSS Domain Audit", "telecom"),
        ]
        for tid, tname, dname in domains:
            graph.add_task(
                TaskNode(
                    task_id=tid,
                    name=tname,
                    description=f"Verify {dname.title()} domain positive, negative, boundary, and defect workflows.",
                    agent_id="DomainAgent",
                    prerequisites=["TASK-02-PLAN"],
                    metadata={"domain": dname},
                )
            )

        # 4. Architectural Layer Audits
        graph.add_task(
            TaskNode(
                task_id="TASK-08-API-AUDIT",
                name="REST API Suite & Contract Audit",
                description="Audit all FastAPI endpoints, response schemas, and defect injection headers.",
                agent_id="APIAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-09-UI-AUDIT",
                name="Playwright UI E2E & Self-Healing Audit",
                description="Audit Chromium user journeys, 3DS flows, and self-healing locator engine.",
                agent_id="UIAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-10-DB-INTEGRITY",
                name="Database Schema & Transaction Invariants",
                description="Verify foreign keys, atomic inventory locks, transaction rollbacks, and persistence.",
                agent_id="APIAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-11-SECURITY-AUDIT",
                name="DAST Security & PCI DSS Masking Audit",
                description="Execute automated DAST scanner for SQLi, XSS, PAN masking, and prompt injection.",
                agent_id="SecurityAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-12-PERFORMANCE-AUDIT",
                name="Performance Latency & SLA Benchmark",
                description="Execute load tests verifying p95 latency under 250ms threshold.",
                agent_id="PerformanceAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-13-RAG-AUDIT",
                name="10-Dimensional AI/RAG Quality Audit",
                description="Evaluate standard, adversarial, hallucination, and refusal RAG test cases.",
                agent_id="RAGAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )
        graph.add_task(
            TaskNode(
                task_id="TASK-14-AGENT-EVAL",
                name="Specialist Agent Benchmark Evaluation",
                description="Evaluate RCA Agent fix synthesis accuracy and Security Testing Agent attack resilience.",
                agent_id="PlanningAgent",
                prerequisites=["TASK-02-PLAN"],
            )
        )

        all_audits = [
            "TASK-03-DOM-AIRLINE", "TASK-04-DOM-HEALTHCARE", "TASK-05-DOM-FINTECH",
            "TASK-06-DOM-ECOMMERCE", "TASK-07-DOM-TELECOM", "TASK-08-API-AUDIT",
            "TASK-09-UI-AUDIT", "TASK-10-DB-INTEGRITY", "TASK-11-SECURITY-AUDIT",
            "TASK-12-PERFORMANCE-AUDIT", "TASK-13-RAG-AUDIT", "TASK-14-AGENT-EVAL"
        ]

        # 5. Defect RCA & Auto-Repair (Runs after audit detections)
        graph.add_task(
            TaskNode(
                task_id="TASK-15-DEFECT-RCA",
                name="Defect RCA & Autonomous Remediation Analysis",
                description="Analyze test results, classify defects, synthesize candidate fixes if needed.",
                agent_id="RCAAgent",
                prerequisites=all_audits,
            )
        )

        # 6. Full Hermetic Regression
        graph.add_task(
            TaskNode(
                task_id="TASK-16-REGRESSION-SUITE",
                name="Full Hermetic Test Regression",
                description="Execute the complete 415 Pytest backend test suite asserting 100% pass rate.",
                agent_id="RegressionAgent",
                prerequisites=["TASK-15-DEFECT-RCA"],
            )
        )

        # 7. Evidence Collection & Normalization
        graph.add_task(
            TaskNode(
                task_id="TASK-17-EVIDENCE-PERSISTENCE",
                name="Structured Telemetry & Evidence Persistence",
                description="Normalize JUnit XML and Playwright reports into latest_evidence.json.",
                agent_id="EvidenceAgent",
                prerequisites=["TASK-16-REGRESSION-SUITE"],
            )
        )

        # 8. Documentation Synchronization
        graph.add_task(
            TaskNode(
                task_id="TASK-18-DOCS-SYNC",
                name="Documentation & Catalog Synchronization",
                description="Synchronize README.md, ROADMAP.md, and master capability inventory.",
                agent_id="DocumentationAgent",
                prerequisites=["TASK-17-EVIDENCE-PERSISTENCE"],
            )
        )

        # 9. Release Governance & Quality Gate
        graph.add_task(
            TaskNode(
                task_id="TASK-19-RELEASE-GATE",
                name="PRODUCTION_STRICT Quality Gate Certification",
                description="Evaluate release readiness under PRODUCTION_STRICT policy and synthesize verdict.",
                agent_id="ReleaseAgent",
                prerequisites=["TASK-18-DOCS-SYNC"],
            )
        )

        goal.tasks = list(graph.tasks.keys())
        self.save_goal(goal)
        return graph

    def update_goal_progress(
        self, goal: GoalDefinition, graph: TaskGraph, final_verdict: Optional[str] = None
    ) -> None:
        """Updates progress percentage, criterion satisfaction, and final verdict."""
        total = len(graph.tasks)
        passed = sum(1 for t in graph.tasks.values() if t.status == "PASSED")
        goal.progress_pct = round((passed / total * 100.0), 1) if total > 0 else 0.0

        # Criteria mappings
        mapping = {
            1: "TASK-01-DISCOVER",
            2: ["TASK-03-DOM-AIRLINE", "TASK-04-DOM-HEALTHCARE", "TASK-05-DOM-FINTECH", "TASK-06-DOM-ECOMMERCE", "TASK-07-DOM-TELECOM"],
            3: "TASK-09-UI-AUDIT",
            4: "TASK-08-API-AUDIT",
            5: "TASK-10-DB-INTEGRITY",
            6: "TASK-11-SECURITY-AUDIT",
            7: "TASK-12-PERFORMANCE-AUDIT",
            8: "TASK-13-RAG-AUDIT",
            9: "TASK-14-AGENT-EVAL",
            10: "TASK-01-DISCOVER",
            11: "TASK-16-REGRESSION-SUITE",
            12: "TASK-15-DEFECT-RCA",
            13: "TASK-15-DEFECT-RCA",
            14: "TASK-16-REGRESSION-SUITE",
            15: "TASK-16-REGRESSION-SUITE",
            16: "TASK-08-API-AUDIT",
            17: "TASK-18-DOCS-SYNC",
            18: "TASK-17-EVIDENCE-PERSISTENCE",
            19: "TASK-15-DEFECT-RCA",
            20: "TASK-19-RELEASE-GATE",
        }

        now_iso = datetime.now(timezone.utc).isoformat()
        for criterion in goal.acceptance_criteria:
            req = mapping.get(criterion.id)
            if isinstance(req, str):
                t = graph.get_task(req)
                if t and t.status == "PASSED":
                    criterion.satisfied = True
                    criterion.verified_at = now_iso
                    criterion.evidence_ref = t.task_id
            elif isinstance(req, list):
                all_ok = all(graph.get_task(tid) and graph.get_task(tid).status == "PASSED" for tid in req)
                if all_ok:
                    criterion.satisfied = True
                    criterion.verified_at = now_iso
                    criterion.evidence_ref = ",".join(req)

        if final_verdict:
            goal.final_verdict = final_verdict
            if final_verdict == "PRODUCTION_READY":
                goal.status = "COMPLETED"
            elif final_verdict == "CONDITIONAL":
                goal.status = "IN_PROGRESS"
            else:
                goal.status = "FAILED"

        self.save_goal(goal)
