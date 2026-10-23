# API Testing Standards

## Contract checks
Validate HTTP status, content type, required fields, field types, enums, schema compatibility, error shape, and documented headers. Prefer repository-owned schemas/contracts over hand-written assumptions.

## Security and behavior
Test authentication and authorization separately; deny unauthorized access by default. Cover invalid/missing fields, malformed JSON, oversized inputs, rate limits where configured, injection payloads, tenant isolation, and sensitive-field leakage.

## State and resilience
Verify persistence and database invariants, idempotency for retryable operations, pagination/filter boundaries, concurrency where relevant, timeouts, upstream failures, and safe error messages.

## UI/API consistency
For critical flows, compare the UI's displayed state with authoritative API/persisted state. Do not make E2E tests depend on undocumented internal implementation details.

## Evidence
Record sanitized request/response metadata, correlation IDs, test ID, environment, and commit SHA. Never store authorization headers or real personal/payment data.
