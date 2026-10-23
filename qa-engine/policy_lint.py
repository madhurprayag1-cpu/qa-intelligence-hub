"""Fail-closed structural checks for the QA governance documents."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SYSTEM_CONTEXT.md", "AGENTS.md", "TEST_STRATEGY.md", "REQUIREMENTS.md",
    "TEST_DATA.md", "LOCATOR_STRATEGY.md", "CODING_STANDARDS.md", "API_TESTING.md",
    "SELF_HEALING.md", "FAILURE_ANALYSIS.md", "COVERAGE_MATRIX.md",
    "EXECUTION_POLICY.md", "REPORTING.md", "SECURITY_GUARDRAILS.md",
    "DEFINITION_OF_DONE.md",
]
MIN_BYTES = 250
errors = []
for name in REQUIRED:
    path = ROOT / name
    if not path.is_file():
        errors.append(f"missing required policy: {name}")
        continue
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) < MIN_BYTES:
        errors.append(f"policy is unexpectedly short: {name}")
    if not content.lstrip().startswith("# "):
        errors.append(f"policy must begin with a Markdown H1: {name}")
    if "TODO" in content or "TBD" in content:
        errors.append(f"unresolved TODO/TBD marker in policy: {name}")

if errors:
    print("Governance policy validation FAILED:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"Governance policy validation PASSED: {len(REQUIRED)} required files present and structurally valid.")
