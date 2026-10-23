# Operational Governance Implementation Matrix

This matrix distinguishes documented policy from executable controls. Shared helpers are
not considered end-to-end production verified until callers invoke them and evidence proves it.

| Policy | Executable control | Evidence | Status |
|---|---|---|---|
| SYSTEM_CONTEXT.md | Shared control functions and revision-bound release evidence | Unit tests | Shared helper implemented |
| AGENTS.md | Action allowlist; unknown actions fail closed | Permission tests | Shared helper implemented; agent wiring pending |
| TEST_STRATEGY.md | Traceability and coverage-gap checks | Mapping tests | Implemented |
| REQUIREMENTS.md | Active requirement IDs linked to enabled tests | Missing/duplicate mapping tests | Implemented |
| TEST_DATA.md | Synthetic-only and environment/data guards | Positive/negative tests | Implemented |
| LOCATOR_STRATEGY.md | Healing proposals restricted to locator changes | Proposal tests | Proposal gate implemented |
| CODING_STANDARDS.md | Strict policy input validation and bounded values | Boundary tests | Implemented |
| API_TESTING.md | Contract-related failure classification | Classification tests | Partial; API contract suites remain separate |
| SELF_HEALING.md | Confidence threshold, protected-domain exclusion, approval, no auto-apply | Proposal tests | Proposal gate implemented |
| FAILURE_ANALYSIS.md | Deterministic first-pass failure categories | Parameterized tests | Implemented; AI analysis remains advisory |
| COVERAGE_MATRIX.md | Unmapped active requirement detection | Gap test | Implemented |
| EXECUTION_POLICY.md | Retry, timeout, worker bounds and production mutation denial | Boundary/permission tests | Helper implemented; callers must enforce result |
| REPORTING.md | Release evidence evaluated against tested revision | Revision-match tests | Gate helper implemented |
| SECURITY_GUARDRAILS.md | Production write denial and synthetic data constraints | Permission/data tests | Helper implemented; security scanners remain required |
| DEFINITION_OF_DONE.md | Fail-closed evidence and quality checks | Missing/mismatch tests | Helper implemented; existing release gate remains authoritative |

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
