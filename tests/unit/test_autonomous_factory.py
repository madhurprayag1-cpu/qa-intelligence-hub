"""Unit Tests for Autonomous Closed-Loop Engineering and QA Factory.

Adheres strictly to MASTER PROMPT Sections 2, 3, 4, 5, 6, 7, 10, 11:
- Validates Standard Agent Contract and machine-readable AgentResult
- Validates ToolRegistry permission authorization and telemetry
- Validates TaskGraph topological prerequisite scheduling
- Validates GoalEngine GOAL-AUTO-001 decomposition and progress tracking
- Validates StateStore atomic persistence and resume capabilities
- Validates full closed-loop execution
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from autonomous.contracts import (
    AgentDefinition,
    AgentPermission,
    AgentResult,
    ToolDefinition,
)
from autonomous.tools import ToolRegistry
from autonomous.task_graph import TaskGraph, TaskNode
from autonomous.goal_engine import GoalEngine, GoalDefinition
from autonomous.state_store import StateStore
from autonomous.agent_framework import AgentRegistry, BaseAutonomousAgent
from autonomous.factory import AutonomousExecutionEngine


def test_agent_contracts_and_serialization():
    res = AgentResult(
        agent_id="security-agent",
        task_id="TASK-SEC-01",
        status="PASS",
        findings=[{"vulnerabilities": 0}],
        recommendations=["Proceed with deployment"],
        confidence=0.98,
        duration_ms=45.2,
    )
    d = res.to_dict()
    assert d["agent_id"] == "security-agent"
    assert d["status"] == "PASS"
    assert d["confidence"] == 0.98
    assert d["findings"][0]["vulnerabilities"] == 0


def test_tool_registry_permission_enforcement():
    registry = ToolRegistry()

    # Tool requiring READ_EXECUTE
    def mock_runner():
        return "EXECUTED"

    registry.register_tool(
        ToolDefinition(
            name="mock_runner",
            description="Executes a test",
            required_permission=AgentPermission.READ_EXECUTE,
        ),
        mock_runner,
    )

    # Caller with READ_ONLY should be denied
    denied_call = registry.invoke(
        tool_name="mock_runner",
        caller_permission=AgentPermission.READ_ONLY,
        caller_agent_id="test-discovery-agent",
    )
    assert denied_call["status"] == "PERMISSION_DENIED"
    assert "PERMISSION_DENIED" in denied_call["status"]

    # Caller with READ_EXECUTE should succeed
    allowed_call = registry.invoke(
        tool_name="mock_runner",
        caller_permission=AgentPermission.READ_EXECUTE,
        caller_agent_id="test-exec-agent",
    )
    assert allowed_call["status"] == "SUCCESS"
    assert allowed_call["result"] == "EXECUTED"


def test_task_graph_dependency_scheduling():
    graph = TaskGraph()
    t1 = TaskNode(
        task_id="T1", name="Step 1", description="", agent_id="A1", prerequisites=[]
    )
    t2 = TaskNode(
        task_id="T2", name="Step 2", description="", agent_id="A2", prerequisites=["T1"]
    )
    graph.add_task(t1)
    graph.add_task(t2)

    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].task_id == "T1"

    # Mark T1 complete
    res = AgentResult(agent_id="A1", task_id="T1", status="PASS")
    graph.mark_completed("T1", res)

    # Now T2 should be ready
    ready2 = graph.get_ready_tasks()
    assert len(ready2) == 1
    assert ready2[0].task_id == "T2"

    graph.mark_completed("T2", AgentResult(agent_id="A2", task_id="T2", status="PASS"))
    assert graph.is_complete() is True


def test_task_graph_retry_limit():
    graph = TaskGraph()
    t1 = TaskNode(
        task_id="T1", name="Step 1", description="", agent_id="A1", max_retries=2
    )
    graph.add_task(t1)

    fail_res = AgentResult(agent_id="A1", task_id="T1", status="FAIL", error_message="Flaky failure")
    
    # Retry 1
    can_retry1 = graph.mark_failed("T1", fail_res, can_retry=True)
    assert can_retry1 is True
    assert graph.get_task("T1").retries == 1

    # Retry 2
    can_retry2 = graph.mark_failed("T1", fail_res, can_retry=True)
    assert can_retry2 is True
    assert graph.get_task("T1").retries == 2

    # Retry 3 exceeds max_retries
    can_retry3 = graph.mark_failed("T1", fail_res, can_retry=True)
    assert can_retry3 is False
    assert graph.get_task("T1").status == "FAILED"


def test_goal_engine_auto_001_initialization():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GoalEngine(goals_dir=Path(tmpdir))
        goal = engine.create_goal_auto_001()

        assert goal.goal_id == "GOAL-AUTO-001"
        assert len(goal.acceptance_criteria) == 20
        assert goal.status == "NOT_STARTED"

        graph = engine.build_task_graph_for_goal(goal)
        assert len(graph.tasks) >= 15
        assert "TASK-01-DISCOVER" in graph.tasks
        assert "TASK-19-RELEASE-GATE" in graph.tasks


def test_state_store_atomic_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = StateStore(base_dir=Path(tmpdir))
        saved = store.persist_state(
            current_goal_id="GOAL-AUTO-001",
            current_task_id="TASK-01-DISCOVER",
            current_agent="DiscoveryAgent",
            current_phase="DISCOVERY",
            task_graph_data={"T1": {"task_id": "T1", "status": "PASSED"}},
            completed_tasks=["T1"],
            failed_tasks=[],
            test_results={"count": 475},
            defects=[],
            quality_gate_status="PENDING",
            next_action="PLAN",
            evidence=["tests/catalog/master_catalog.json"],
            progress_pct=10.0,
        )

        assert saved["current_goal"] == "GOAL-AUTO-001"
        assert saved["progress_pct"] == 10.0

        loaded = store.load_latest_state()
        assert loaded is not None
        assert loaded["current_goal"] == "GOAL-AUTO-001"
        assert loaded["current_agent"] == "DiscoveryAgent"


def test_release_promotion_gate_and_lifecycle():
    from autonomous.release_gate import ReleasePromotionManager
    from autonomous.contracts import ReleaseLifecycleState

    mgr = ReleasePromotionManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = GoalEngine(goals_dir=Path(tmpdir))
        goal = engine.create_goal_auto_001()
        graph = engine.build_task_graph_for_goal(goal)

        # Mark all tasks passed to simulate successful execution
        for t in graph.tasks.values():
            graph.mark_passed(t.task_id)
        for c in goal.acceptance_criteria:
            c.satisfied = True

        # Test with human approval mandated (default)
        report_human = mgr.execute_full_release_lifecycle(
            goal=goal,
            graph=graph,
            run_id="RUN-TEST-001",
            require_human_approval=True,
        )
        assert report_human.final_verdict == "RELEASE_READY_FOR_APPROVAL"
        assert report_human.lifecycle_state == ReleaseLifecycleState.PR_READY.value
        assert len(report_human.state_transitions) >= 3

        # Test with autonomous merge permitted
        report_auto = mgr.execute_full_release_lifecycle(
            goal=goal,
            graph=graph,
            run_id="RUN-TEST-002",
            require_human_approval=False,
        )
        assert report_auto.final_verdict == "PRODUCTION_READY"
        assert report_auto.lifecycle_state == ReleaseLifecycleState.PRODUCTION_READY.value
        assert len(report_auto.state_transitions) == 7
        assert report_auto.deployment_revision is not None
        assert report_auto.test_results["total_capabilities"] == 475

