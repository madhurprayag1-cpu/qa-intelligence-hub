# Test Data Policy

## Principles
Use synthetic, minimal, non-identifying data by default. Never copy production personal data, credentials, tokens, payment data, or customer payloads into fixtures, prompts, screenshots, traces, or reports.

## Design
Maintain explicit fixtures/builders for valid, invalid, boundary, missing, duplicate, expired, unauthorized, and inconsistent data. Make time, randomness, and external dependencies deterministic where possible.

## Lifecycle
Create data per test or isolated test run; namespace shared records; clean up only resources created by the test. Cleanup failures must be visible. Avoid destructive cleanup against shared or production systems.

## Secrets and sensitive values
Inject secrets through approved CI secret stores/environment variables; never commit them or echo them. Redact authorization headers, cookies, PII and payment data before artifact upload. Rotate exposed credentials immediately.

## Environment boundary
Production tests are read-only smoke checks unless a separately approved, reversible test procedure exists. Validate target host and environment before any mutation.
