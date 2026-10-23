# Test Execution Policy

## Environment controls
Default to local/CI test environments. Validate configured base URL, database URL, and environment before execution. Production smoke is read-only; mutations require documented authorization and a safe rollback plan.

## Timeouts and retries
Set explicit test, assertion, request, and job timeouts. Use bounded retries only for known transient conditions; preserve first-attempt failures and retry counts. Do not retry deterministic assertion failures to manufacture a pass.

## Parallelism and isolation
Parallelize only tests with isolated data and independent state. Use unique data namespaces, deterministic fixtures, and cleanup ownership. Limit concurrency for rate-limited/shared services.

## Quarantine
Flaky tests remain visible and tracked with owner, issue, expiry date, and reason. Quarantine cannot hide P0/P1 behavior or make a required release gate green.

## Cancellation and artifacts
Honor cancellation; retain sanitized failure evidence. Mark missing/partial artifacts as incomplete. Release gates must fail closed when required evidence is missing, stale, or tied to a different revision.
