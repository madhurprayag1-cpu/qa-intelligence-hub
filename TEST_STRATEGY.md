# Test Strategy

## Scope
Cover frontend journeys, API contracts and authorization, database invariants, integrations, AI/RAG behavior, security controls, performance-sensitive paths, and release workflows.

## Risk-based priority
P0: data loss, privilege escalation, secret exposure, release-gate bypass. P1: critical user flows, payment/booking integrity, authentication and core APIs. P2: common alternate flows and integration failures. P3: cosmetic or low-impact behavior. Adjust priority using likelihood, impact, exposure, and detectability.

## Test layers
- Unit: deterministic business rules and edge conditions.
- API/integration: status, schema, auth, persistence, idempotency, error contracts.
- UI E2E: critical user journeys and accessible interaction.
- Security: SAST, dependency audit, secret scan, DAST and negative authorization tests.
- AI/RAG: groundedness, refusal behavior, prompt-injection resistance and deterministic benchmark checks.
- Release: revision-bound artifacts, required job outcomes, serving-SHA verification and read-only production smoke.

## Scenario dimensions
Positive, negative, boundary, equivalence classes, state transitions, concurrency/idempotency, localization/time, accessibility, browser compatibility, recovery and regression.

## Reliability
Retries are not a substitute for fixing flaky tests. Record retry history; quarantine only with an owner, issue, expiry and retained visibility. Critical failures must not be hidden by retries.

## Exit criteria
All required CI jobs pass; no untriaged P0/P1 defects; security policy passes; evidence is tied to the tested SHA; coverage gaps and approved exceptions are documented. Thresholds must be configured in executable gates, not merely stated here.
