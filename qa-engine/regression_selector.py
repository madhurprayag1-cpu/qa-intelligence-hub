from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class RegressionPlan:
    changed_files: List[str]
    selected_test_files: List[str]
    selected_tags: List[str]
    pytest_command: str
    playwright_command: str | None = None
    reasoning: List[str] = field(default_factory=list)
    active_domain: str = "airline"


from domains.airline.regression_map import AIRLINE_REGRESSION_PATTERNS

CORE_FILE_MAP: Dict[str, Dict[str, List[str]]] = {
    "defects": {
        "patterns": ["defect"],
        "tests": [
            "tests/api/test_defects.py",
        ],
        "tags": ["defect"],
        "ui_specs": ["tests/ui/qa_platform_e2e.spec.ts"],
    },
    "quality_gate": {
        "patterns": ["quality_gate", "registry"],
        "tests": [
            "tests/unit/test_quality_gate.py",
            "tests/api/test_quality_gate_api.py",
        ],
        "tags": ["gate"],
        "ui_specs": ["tests/ui/qa_platform_e2e.spec.ts"],
    },
    "ai_rag": {
        "patterns": ["ai-engine", "routers/ai", "/ai", "_ai", "rag", "agent", "embedding", "llm"],
        "tests": [
            "tests/ai/test_ai_platform.py",
            "tests/ai/test_production_rag.py",
            "tests/ai/test_rag_quality_gate.py",
            "tests/unit/test_ai_engine.py",
        ],
        "tags": ["ai", "rag"],
        "ui_specs": ["tests/ui/qa_platform_e2e.spec.ts"],
    },
    "database": {
        "patterns": ["models", "alembic", "database", "schema", "db/"],
        "tests": [
            "tests/database/test_database_invariants.py",
            "tests/api/test_bookings.py",
        ],
        "tags": ["database", "booking"],
        "ui_specs": [],
    },
    "security": {
        "patterns": ["auth", "security", "jwt", "idor", "rbac"],
        "tests": [
            "tests/security/test_security_suite.py",
            "tests/security/test_auth_rbac_idor.py",
            "tests/agents/test_security_agent.py",
        ],
        "tags": ["security", "auth"],
        "ui_specs": ["tests/ui/qa_platform_e2e.spec.ts"],
    },
    "contract": {
        "patterns": ["openapi", "contract", "schemas"],
        "tests": [
            "tests/contract/test_openapi_contract.py",
        ],
        "tags": ["contract"],
        "ui_specs": [],
    },
    "performance": {
        "patterns": ["benchmark", "latency", "throughput", "concurrency"],
        "tests": [
            "tests/performance/test_performance_benchmarks.py",
        ],
        "tags": ["performance"],
        "ui_specs": [],
    },
    "frontend": {
        "patterns": ["frontend", "App.tsx", "index.css", "api.ts"],
        "tests": [],
        "tags": ["ui"],
        "ui_specs": ["tests/ui/booking_3ds_e2e.spec.ts", "tests/ui/qa_platform_e2e.spec.ts"],
    },
}
 
def get_effective_file_map() -> Dict[str, Dict[str, List[str]]]:
    """Dynamically aggregates regression patterns across core platform and all registered domain packs."""
    merged: Dict[str, Dict[str, List[str]]] = dict(CORE_FILE_MAP)
    merged.update(AIRLINE_REGRESSION_PATTERNS)
    try:
        from domain_registry import domain_registry
        for pack in domain_registry.list_domains():
            if pack.regression_patterns:
                merged.update(pack.regression_patterns)
    except Exception:
        pass
    return merged


# Unified regression map combining active domain patterns with core platform patterns
FILE_MAP: Dict[str, Dict[str, List[str]]] = {
    **AIRLINE_REGRESSION_PATTERNS,
    **CORE_FILE_MAP,
}


def select_regression_tests(
    changed_files: List[str],
    domain_id: Optional[str] = None,
    scope_to_domain: bool = False,
) -> RegressionPlan:
    """Smart regression selector determining minimal test impact set (AGENTS.md Section 5)."""
    selected_tests: Set[str] = set()
    selected_tags: Set[str] = set()
    selected_ui: Set[str] = set()
    reasons: List[str] = []

    try:
        from domain_registry import domain_registry
        active_domain = (domain_id or domain_registry.get_active_domain_id()).lower()
    except Exception:
        active_domain = (domain_id or "airline").lower()

    if scope_to_domain:
        scoped_map: Dict[str, Dict[str, List[str]]] = dict(CORE_FILE_MAP)
        try:
            from domain_registry import domain_registry
            pack = domain_registry.get(active_domain)
            if pack and pack.regression_patterns:
                scoped_map.update(pack.regression_patterns)
        except Exception:
            pass
        effective_file_map = scoped_map
    else:
        effective_file_map = get_effective_file_map()

    for f in changed_files:
        f_lower = f.lower()
        matched = False
        for category, config in effective_file_map.items():
            if any(p in f_lower for p in config["patterns"]):
                for t in config["tests"]:
                    selected_tests.add(t)
                for tg in config["tags"]:
                    selected_tags.add(tg)
                for ui in config.get("ui_specs", []):
                    selected_ui.add(ui)
                reasons.append(f"Changed '{f}' mapped to category '{category}'")
                matched = True

        if not matched:
            # Fallback if unknown or root config changed: select full API suite
            selected_tests.add("tests/api/")
            reasons.append(f"Uncategorized change '{f}' triggered default API regression layer")

    test_file_list = sorted(list(selected_tests))
    tag_list = sorted(list(selected_tags))
    ui_list = sorted(list(selected_ui))

    pytest_cmd = f"pytest {' '.join(test_file_list)}" if test_file_list else "pytest tests/"
    playwright_cmd = f"npx playwright test {' '.join(ui_list)}" if ui_list else None

    return RegressionPlan(
        changed_files=changed_files,
        selected_test_files=test_file_list,
        selected_tags=tag_list,
        pytest_command=pytest_cmd,
        playwright_command=playwright_cmd,
        reasoning=reasons,
        active_domain=active_domain,
    )
