# Requirements and Traceability

## Requirement record
Each requirement should have a stable ID, source/owner, business rationale, priority/risk, acceptance criteria, dependencies, and verification method.

## Acceptance criteria
Write observable, testable outcomes. Prefer Given/When/Then where useful. Include failure behavior, authorization, data validation, auditability, and relevant non-functional expectations.

## Traceability
Map `REQ-*` → test IDs/specs → execution result → defect/exception → evidence artifact and commit SHA. Do not mark a requirement covered solely because a test file exists; require an executed result.

## Change control
Requirement changes must identify impacted tests, fixtures, API schemas, documentation, and release risks. Unclear requirements are explicitly marked blocked/assumption-required rather than invented by an agent.

## Template
- ID / title:
- Source / owner:
- Priority and risk:
- Preconditions and dependencies:
- Acceptance criteria:
- Positive / negative / boundary scenarios:
- Security and privacy considerations:
- Test IDs and evidence:
- Status / approved exceptions:
