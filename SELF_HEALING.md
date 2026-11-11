# Controlled Self-Healing Policy

## Supported behavior
The system may diagnose locator failures and suggest alternate selectors using DOM/accessibility snapshots and test context. Suggestions are candidates, not automatic fixes.

## Required validation
- Candidate resolves to exactly one element.
- Role/name/label and intended behavior match the original requirement.
- No weakened assertion, removed step, or skipped test is introduced.
- Targeted test and relevant regression pass.
- Before/after evidence and proposed diff are retained for review.

## Confidence and approvals
A model confidence score is insufficient by itself. Source changes require human review and normal branch/CI controls. No self-healing is permitted for authorization, security, payment, destructive, or release-gate assertions without explicit specialist review.

## Audit
Record failure signature, candidate locator, validation results, reviewer, final decision, and expiry of temporary workarounds. Never silently rewrite committed tests during a production run.
