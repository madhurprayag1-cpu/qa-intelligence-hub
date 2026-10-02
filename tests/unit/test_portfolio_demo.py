"""Unit tests for Unified End-to-End Portfolio Demonstration Runner.

Verifies:
- All 7 QE modules execute synchronously and asynchronously without error.
- Returns PASSED status and 7/7 passed modules.
- Formatted output and CLI arguments work as expected.
"""

import pytest
from portfolio_demo import run_portfolio_demonstration, PortfolioDemoReport


@pytest.mark.anyio
async def test_run_portfolio_demonstration_success():
    """Verify that run_portfolio_demonstration completes with PASSED and all 7 modules pass."""
    report: PortfolioDemoReport = await run_portfolio_demonstration(verbose=False)

    assert report.overall_status == "PASSED"
    assert report.total_modules == 7
    assert report.passed_modules == 7
    assert report.failed_modules == 0
    assert report.total_duration_ms > 0

    expected_modules = {
        "M1_DOMAIN_REGISTRY",
        "M2_DATA_FACTORIES",
        "M3_DEFECT_ENGINEERING",
        "M4_RAG_PIPELINE",
        "M5_SPECIALIST_AGENTS",
        "M6_REGRESSION_SELECTOR",
        "M7_QUALITY_GATE",
    }
    actual_modules = {mod.module_id for mod in report.modules}
    assert actual_modules == expected_modules

    for mod in report.modules:
        assert mod.status == "PASSED"
        assert mod.elapsed_ms >= 0
        assert len(mod.summary) > 0


def test_portfolio_demo_cli_execution():
    """Verify that portfolio_demo CLI runs and exits with status code 0."""
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "qa-engine/portfolio_demo.py", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.returncode == 0
    assert '"overall_status": "PASSED"' in res.stdout
    assert '"passed_modules": 7' in res.stdout

