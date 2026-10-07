"""Persistent Resumable Execution State Store.

Adheres strictly to MASTER PROMPT Section 6:
- Persists machine-readable state to .qa/autonomous/
- Directories: goals/, tasks/, runs/, events/, evidence/, locks/
- Captures run metadata, active task, commit SHA, quality gate status, and next action
- Supports uninterrupted resumption upon process restarts
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class StateStore:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (_REPO_ROOT / ".qa" / "autonomous")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.goals_dir = self.base_dir / "goals"
        self.tasks_dir = self.base_dir / "tasks"
        self.runs_dir = self.base_dir / "runs"
        self.events_dir = self.base_dir / "events"
        self.evidence_dir = self.base_dir / "evidence"
        self.locks_dir = self.base_dir / "locks"

        for d in [
            self.goals_dir, self.tasks_dir, self.runs_dir,
            self.events_dir, self.evidence_dir, self.locks_dir
        ]:
            d.mkdir(parents=True, exist_ok=True)

        self.state_file = self.base_dir / "state.json"

    def _get_git_info(self) -> Dict[str, str]:
        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT), text=True
            ).strip()
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], cwd=str(_REPO_ROOT), text=True
            ).strip()
            return {"commit_sha": sha, "branch": branch}
        except Exception:
            return {"commit_sha": "UNKNOWN", "branch": "UNKNOWN"}

    def persist_state(
        self,
        current_goal_id: str,
        current_task_id: Optional[str],
        current_agent: Optional[str],
        current_phase: str,
        task_graph_data: Dict[str, Any],
        completed_tasks: List[str],
        failed_tasks: List[str],
        test_results: Dict[str, Any],
        defects: List[Dict[str, Any]],
        quality_gate_status: str,
        next_action: str,
        evidence: List[str],
        progress_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Saves current execution snapshot atomically to state.json."""
        git_info = self._get_git_info()
        now_ts = datetime.now(timezone.utc).isoformat()

        state_payload = {
            "timestamp": now_ts,
            "current_goal": current_goal_id,
            "current_task": current_task_id,
            "current_agent": current_agent,
            "current_phase": current_phase,
            "progress_pct": progress_pct,
            "branch": git_info["branch"],
            "current_commit": git_info["commit_sha"],
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "quality_gate_status": quality_gate_status,
            "next_action": next_action,
            "task_graph": task_graph_data,
            "test_results": test_results,
            "defects": defects,
            "evidence": evidence,
        }

        # Atomic write
        tmp_file = self.state_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        tmp_file.replace(self.state_file)

        return state_payload

    def load_latest_state(self) -> Optional[Dict[str, Any]]:
        """Loads state.json if present for seamless task resumption."""
        if not self.state_file.exists():
            return None
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def record_event(
        self,
        event_type: str,
        description: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends structured lifecycle event log."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "description": description,
            "agent_id": agent_id,
            "task_id": task_id,
            "metadata": metadata or {},
        }
        day_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        event_file = self.events_dir / f"events-{day_str}.jsonl"
        with open(event_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def save_run_record(self, run_id: str, report_data: Dict[str, Any]) -> None:
        run_file = self.runs_dir / f"{run_id}.json"
        run_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    def acquire_lock(self, lock_name: str) -> bool:
        lock_file = self.locks_dir / f"{lock_name}.lock"
        if lock_file.exists():
            return False
        lock_file.write_text(
            f"PID={os.getpid()} TIME={datetime.now(timezone.utc).isoformat()}",
            encoding="utf-8",
        )
        return True

    def release_lock(self, lock_name: str) -> None:
        lock_file = self.locks_dir / f"{lock_name}.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
            except OSError:
                pass
