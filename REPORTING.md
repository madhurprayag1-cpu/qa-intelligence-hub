# Reporting and Evidence

## Minimum report fields
Run ID; source commit SHA; branch; environment; start/end time; tool/version; test totals (passed/failed/skipped/retried); failures; security/RAG gate results; artifact links; and known limitations.

## Failure evidence
Attach sanitized stack traces, screenshots/traces, request/response excerpts, and correlation IDs when relevant. Remove secrets, cookies, tokens, PII, and payment data before upload.

## CI/release summary
Separate catalog size from discovered, executed, passed, failed, skipped, and historical counts. Report each job's actual result. Do not use a simulated run as CI evidence or infer production deployment from a successful build.

## Notifications
Notify on required gate failures, missing artifacts, stale revision mismatches, and release status changes. Include actionable links and ownership; avoid noisy duplicate alerts.

## Retention
Follow repository/org artifact retention settings and applicable privacy requirements. Document where evidence is stored and who can access it.
