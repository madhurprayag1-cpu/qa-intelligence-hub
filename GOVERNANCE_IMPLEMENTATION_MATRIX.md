# Operational Governance Implementation Matrix

This matrix distinguishes documented policy from executable controls. Shared helpers are
not considered end-to-end production verified until callers invoke them and evidence proves it.

| Policy | Executable control | Evidence | Status |
|---|---|---|---|
| SYSTEM_CONTEXT.md | Shared control functions and revision-bound release evidence | Unit tests | Shared helper implemented |
| AGENTS.md | MCP dispatcher and autonomous ToolRegistry enforce allowlists and deny unregistered/unauthorized actions before handlers run | Dispatcher and registry denial-path tests | Shared runtime entry points integrated; other agent classes remain subject to entry-point audit |
| TEST_STRATEGY.md | Traceability and coverage-gap checks | Mapping tests | Implemented |
| REQUIREMENTS.md | Active requirement IDs linked to enabled tests | Missing/duplicate mapping tests | Implemented |
| TEST_DATA.md | Synthetic-only and environment/data guards | Positive/negative tests | Implemented |
| LOCATOR_STRATEGY.md | Healing proposals restricted to locator changes | Proposal tests | Proposal gate implemented |
| CODING_STANDARDS.md | Strict policy input validation and bounded values | Boundary tests | Implemented |
| API_TESTING.md | Contract-related failure classification | Classification tests | Partial; API contract suites remain separate |
| SELF_HEALING.md | Confidence threshold, protected-domain exclusion, approval, no auto-apply | Proposal tests | Proposal gate implemented |
| FAILURE_ANALYSIS.md | Deterministic first-pass failure categories | Parameterized tests | Implemented; AI analysis remains advisory |
| COVERAGE_MATRIX.md | Unmapped active requirement detection | Gap test | Implemented |
| EXECUTION_POLICY.md | Bounded retry/timeout/worker settings fail closed; ToolRegistry and MasterOrchestrator bound subprocesses; remediation regression subprocesses are time-limited and prohibited in production | Boundary tests, invalid-policy denial, production-write denial, orchestration timeout denial, remediation production/timeout denial | Runtime registry, direct test/security orchestration, and remediation regression paths integrated |
| REPORTING.md | ReportingAgent calls the Definition-of-Done gate and requires explicit security, coverage, human-review, matching tested/release revisions, zero skipped tests, and retained evidence before GO | Positive and missing-evidence reporting tests | Runtime report sign-off is evidence-bound; CI checkpoint remains independently authoritative |
| SECURITY_GUARDRAILS.md | Production write denial and synthetic data constraints | Permission/data tests | Helper implemented; security scanners remain required |
| DEFINITION_OF_DONE.md | ReportingAgent invokes evaluate_definition_of_done; missing or mismatched evidence forces NO-GO | Positive/missing-evidence report tests plus helper unit tests | Integrated into report generation; final CI checkpoint still validates actual artifacts and SHA |

## Integration contract

- A failed result is a hard stop for any caller; do not treat it as a warning.
- These helpers do not execute generated code, change locators, or deploy releases.
- Production mutations are denied even when an approval name is supplied.
- Healing is proposal-only, requires a human approval flag, excludes protected domains,
  and rejects automatic application.
- Existing CI, DAST/SAST/dependency/secret scans, E2E tests, and revision-bound checkpoint
  remain required. These controls supplement rather than replace those systems.
- Do not mark a policy end-to-end or production verified until real caller integration and
  deployment evidence exist.
