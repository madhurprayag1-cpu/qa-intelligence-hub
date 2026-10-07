"""Standard Agent Contract and Definition-of-Done Schemas.

Adheres strictly to MASTER PROMPT Sections 2, 3, 10, 11:
- Reusable Standard Agent Contract
- Explicit permissions per role
- Machine-readable structured results
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AgentPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    READ_EXECUTE = "READ_EXECUTE"
    READ_ANALYZE = "READ_ANALYZE"
    READ_WRITE_BRANCH = "READ_WRITE_BRANCH"
    RELEASE = "RELEASE"
    PRODUCTION_READ_ONLY = "PRODUCTION_READ_ONLY"


class ReleaseLifecycleState(str, Enum):
    """Adheres strictly to MASTER PROMPT Section 31 (7 distinct release states)."""
    DEVELOPMENT_COMPLETE = "DEVELOPMENT_COMPLETE"
    QUALITY_GATE_PASSED = "QUALITY_GATE_PASSED"
    PR_READY = "PR_READY"
    MERGED_TO_MAIN = "MERGED_TO_MAIN"
    DEPLOYMENT_READY = "DEPLOYMENT_READY"
    PRODUCTION_VERIFIED = "PRODUCTION_VERIFIED"
    PRODUCTION_READY = "PRODUCTION_READY"


@dataclass
class ToolDefinition:
    name: str
    description: str
    required_permission: AgentPermission
    parameters_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentDefinition:
    agent_id: str
    name: str
    role: str
    objective: str
    permission: AgentPermission
    allowed_tools: List[str]
    constraints: List[str]
    success_criteria: List[str]
    failure_policy: str  # "RETRY" | "FAIL_CLOSED" | "ESCALATE"
    retry_policy: Dict[str, Any] = field(
        default_factory=lambda: {"max_attempts": 3, "backoff_sec": 1.0}
    )
    evidence_requirements: List[str] = field(default_factory=list)


@dataclass
class AgentResult:
    agent_id: str
    task_id: str
    status: str  # "PASS" | "FAIL" | "BLOCKED" | "DEGRADED"
    findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    next_action: str = "CONTINUE"
    confidence: float = 1.0
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
