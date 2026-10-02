"""Regression Test Selection & Impact Analysis Tests.

Adheres strictly to AGENTS.md Section 11 (Regression Layer) & Section 12 (Test Data & Execution):
- Verifies intelligent regression test impact analysis from PR git diffs
- Validates file-to-test mapping across payments, bookings, database, security, contracts, AI/RAG, and UI
- Verifies multi-file PR diff union resolution without test duplication
- Verifies safe fallback to broad API test layer for uncategorized changes
- Verifies deterministic CLI execution command generation for pytest and Playwright
- Verifies tag filtering interoperability with TestRegistry
"""

import pytest
from regression_selector import select_regression_tests, RegressionPlan, FILE_MAP
from test_registry import TestRegistry, TestCase


def test_regression_selector_payment_diff():
    """Modifying payments code triggers payment API tests, security suite, and 3DS UI specs."""
    diff = ["backend/app/routers/payments.py"]
    plan = select_regression_tests(diff)

    assert "tests/api/test_payments.py" in plan.selected_test_files
    assert "tests/security/test_security_suite.py" in plan.selected_test_files
    assert "payment" in plan.selected_tags
    assert "security" in plan.selected_tags
    assert plan.playwright_command is not None
    assert "booking_3ds_e2e.spec.ts" in plan.playwright_command
    assert any("mapped to category 'payments'" in r for r in plan.reasoning)


def test_regression_selector_booking_diff():
    """Modifying bookings code triggers booking tests, defect tests, and UI specs."""
    diff = ["backend/app/routers/bookings.py"]
    plan = select_regression_tests(diff)

    assert "tests/api/test_bookings.py" in plan.selected_test_files
    assert "tests/api/test_defects.py" in plan.selected_test_files
    assert "booking" in plan.selected_tags
    assert "defect" in plan.selected_tags
    assert plan.playwright_command is not None


def test_regression_selector_database_models_diff():
    """Modifying database schema or migrations triggers database invariants and booking suites."""
    diff = ["alembic/versions/001_initial_schema.py", "backend/app/db/database.py"]
    plan = select_regression_tests(diff)

    assert "tests/database/test_database_invariants.py" in plan.selected_test_files
    assert "tests/api/test_bookings.py" in plan.selected_test_files
    assert "database" in plan.selected_tags
    # Pure DB schema changes do not require UI specs by default
    assert plan.playwright_command is None


def test_regression_selector_ai_rag_diff():
    """Modifying AI engine or RAG pipelines triggers AI platform and unit tests."""
    diff = ["ai-engine/rag.py", "ai-engine/agents.py"]
    plan = select_regression_tests(diff)

    assert "tests/ai/test_ai_platform.py" in plan.selected_test_files
    assert "tests/unit/test_ai_engine.py" in plan.selected_test_files
    assert "ai" in plan.selected_tags
    assert "rag" in plan.selected_tags
    assert plan.playwright_command is not None
    assert "qa_platform_e2e.spec.ts" in plan.playwright_command


def test_regression_selector_security_auth_diff():
    """Modifying auth or RBAC triggers full security, IDOR, and Security Agent tests."""
    diff = ["backend/app/core/auth.py"]
    plan = select_regression_tests(diff)

    assert "tests/security/test_security_suite.py" in plan.selected_test_files
    assert "tests/security/test_auth_rbac_idor.py" in plan.selected_test_files
    assert "tests/agents/test_security_agent.py" in plan.selected_test_files
    assert "security" in plan.selected_tags
    assert "auth" in plan.selected_tags


def test_regression_selector_contract_diff():
    """Modifying schemas or OpenAPI specs triggers contract testing suite."""
    diff = ["backend/app/schemas/openapi_specs.json"]
    plan = select_regression_tests(diff)

    assert "tests/contract/test_openapi_contract.py" in plan.selected_test_files
    assert "contract" in plan.selected_tags
    assert plan.playwright_command is None


def test_regression_selector_performance_diff():
    """Modifying performance benchmarks triggers performance benchmark test suite."""
    diff = ["tests/performance/latency_benchmarks.py"]
    plan = select_regression_tests(diff)

    assert "tests/performance/test_performance_benchmarks.py" in plan.selected_test_files
    assert "performance" in plan.selected_tags


def test_regression_selector_frontend_diff():
    """Modifying frontend UI components triggers Playwright E2E suite."""
    diff = ["frontend/src/App.tsx", "frontend/src/index.css"]
    plan = select_regression_tests(diff)

    assert "ui" in plan.selected_tags
    assert plan.playwright_command is not None
    assert "booking_3ds_e2e.spec.ts" in plan.playwright_command
    assert "qa_platform_e2e.spec.ts" in plan.playwright_command


def test_regression_selector_multi_file_pr_union():
    """PR touching both payments and database selects deduplicated union of impacted tests."""
    diff = [
        "backend/app/routers/payments.py",
        "backend/app/models/payment.py",
    ]
    plan = select_regression_tests(diff)

    # Should contain payment tests AND database invariant tests
    assert "tests/api/test_payments.py" in plan.selected_test_files
    assert "tests/database/test_database_invariants.py" in plan.selected_test_files
    assert "tests/security/test_security_suite.py" in plan.selected_test_files

    # Ensure no duplicates in test file list
    assert len(plan.selected_test_files) == len(set(plan.selected_test_files))
    assert len(plan.reasoning) >= 2


def test_regression_selector_fallback_on_unrecognized_file():
    """Unrecognized root changes safely fall back to full API regression layer."""
    diff = ["docker/compose.yaml", "infra/terraform/main.tf"]
    plan = select_regression_tests(diff)

    assert "tests/api/" in plan.selected_test_files
    assert any("triggered default API regression layer" in r for r in plan.reasoning)


def test_regression_selector_command_generation():
    """Generated CLI commands must be valid strings executable in CI pipelines."""
    diff = ["backend/app/routers/payments.py"]
    plan = select_regression_tests(diff)

    assert plan.pytest_command.startswith("pytest ")
    for test_file in plan.selected_test_files:
        assert test_file in plan.pytest_command

    assert plan.playwright_command.startswith("npx playwright test ")


def test_regression_tag_registry_interoperability():
    """All regression tags generated by FILE_MAP can be looked up in TestRegistry."""
    registry = TestRegistry()

    # Register representative test cases matching all categories
    registry.register(TestCase(id="TC-PAY-01", name="Payment Flow", layer="api", tags=("payment", "security")))
    registry.register(TestCase(id="TC-BOOK-01", name="Booking Flow", layer="api", tags=("booking", "defect")))
    registry.register(TestCase(id="TC-SRCH-01", name="Flight Search", layer="api", tags=("search", "flight")))
    registry.register(TestCase(id="TC-DB-01", name="DB Invariants", layer="database", tags=("database", "booking")))
    registry.register(TestCase(id="TC-AI-01", name="RAG Pipeline", layer="ai", tags=("ai", "rag")))
    registry.register(TestCase(id="TC-SEC-01", name="IDOR Protection", layer="security", tags=("security", "auth")))
    registry.register(TestCase(id="TC-CTR-01", name="OpenAPI Schema", layer="contract", tags=("contract",)))
    registry.register(TestCase(id="TC-GATE-01", name="Quality Gate", layer="unit", tags=("gate",)))
    registry.register(TestCase(id="TC-PERF-01", name="Latency Check", layer="performance", tags=("performance",)))
    registry.register(TestCase(id="TC-UI-01", name="Dashboard UI", layer="ui", tags=("ui",)))

    # For each category in FILE_MAP, verify that registered tags retrieve test cases
    for category, config in FILE_MAP.items():
        for tag in config["tags"]:
            matching_tests = registry.by_tag(tag)
            assert len(matching_tests) > 0, f"Tag '{tag}' in category '{category}' should match test registry"
