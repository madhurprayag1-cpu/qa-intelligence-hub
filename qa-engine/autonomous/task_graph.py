"""Dependency Task Graph Engine for Autonomous Execution.

Adheres strictly to MASTER PROMPT Section 5:
- Converts goals into structured dependency graphs
- Enforces prerequisite topological ordering
- Identifies independent tasks suitable for concurrent or prioritized dispatch
- Tracks retry counts (max 3), blockers, and execution state
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from autonomous.contracts import AgentResult


@dataclass
class TaskNode:
    task_id: str
    name: str
    description: str
    agent_id: str
    prerequisites: List[str] = field(default_factory=list)
    status: str = "PENDING"  # "PENDING" | "READY" | "RUNNING" | "PASSED" | "FAILED" | "BLOCKED" | "SKIPPED"
    retries: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    evidence_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        return cls(**data)


class TaskGraph:
    """Directed acyclic dependency graph managing task execution flow."""

    def __init__(self, tasks: Optional[Dict[str, TaskNode]] = None):
        self.tasks: Dict[str, TaskNode] = tasks or {}

    def add_task(self, task: TaskNode) -> None:
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns all tasks whose prerequisites have passed and are in PENDING or READY state."""
        ready: List[TaskNode] = []
        for task in self.tasks.values():
            if task.status in ["PENDING", "READY"]:
                prereqs_satisfied = True
                for p_id in task.prerequisites:
                    prereq = self.tasks.get(p_id)
                    if not prereq or prereq.status != "PASSED":
                        prereqs_satisfied = False
                        break
                if prereqs_satisfied:
                    task.status = "READY"
                    ready.append(task)
        return ready

    def get_next_task(self) -> Optional[TaskNode]:
        ready = self.get_ready_tasks()
        return ready[0] if ready else None

    def mark_running(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task:
            task.status = "RUNNING"

    def mark_completed(self, task_id: str, result: Optional[AgentResult] = None) -> None:
        task = self.tasks.get(task_id)
        if task:
            task.status = "PASSED"
            if result:
                task.result = result.to_dict()
                if result.evidence:
                    task.evidence_paths = [
                        ev.get("path", "") for ev in result.evidence if "path" in ev
                    ]

    def mark_passed(self, task_id: str, result: Optional[AgentResult] = None) -> None:
        self.mark_completed(task_id, result)

    def mark_failed(
        self, task_id: str, result: AgentResult, can_retry: bool = True
    ) -> bool:
        """Marks a task failed and determines if retry is permissible (max 3)."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.result = result.to_dict()
        task.failure_reason = result.error_message or (
            result.findings[0].get("description") if result.findings else "Execution failed"
        )

        if can_retry and task.retries < task.max_retries:
            task.retries += 1
            task.status = "READY"
            return True  # Will retry
        else:
            task.status = "FAILED"
            # Block dependent tasks
            self._propagate_block(task_id)
            return False

    def _propagate_block(self, failed_task_id: str) -> None:
        for task in self.tasks.values():
            if failed_task_id in task.prerequisites and task.status in ["PENDING", "READY"]:
                task.status = "BLOCKED"
                self._propagate_block(task.task_id)

    def is_complete(self) -> bool:
        return all(t.status in ["PASSED", "SKIPPED"] for t in self.tasks.values())

    def has_failures(self) -> bool:
        return any(t.status == "FAILED" for t in self.tasks.values())

    def has_unresolved_blockers(self) -> bool:
        return any(t.status == "BLOCKED" for t in self.tasks.values())

    def get_summary(self) -> Dict[str, Any]:
        counts = {
            "total": len(self.tasks),
            "passed": 0,
            "failed": 0,
            "running": 0,
            "ready": 0,
            "pending": 0,
            "blocked": 0,
            "skipped": 0,
        }
        for t in self.tasks.values():
            st = t.status.lower()
            if st in counts:
                counts[st] += 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {tid: t.to_dict() for tid, t in self.tasks.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskGraph":
        tasks = {tid: TaskNode.from_dict(tdata) for tid, tdata in data.items()}
        return cls(tasks)
