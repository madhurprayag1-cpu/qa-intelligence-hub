# Failure Analysis and Root Cause

## Evidence first
Collect the exact test ID, run ID, commit SHA, environment, timestamp/timezone, sanitized logs, stack trace, screenshots/trace, request/response metadata, and dependency/service health.

## Classification
Classify as product defect, automation/test defect, test-data issue, environment/dependency issue, timing/race, or inconclusive. A symptom or error message alone is not a root cause.

## Analysis method
1. Establish expected versus actual behavior.
2. Reconstruct the timeline and correlate IDs.
3. Identify the first causal divergence, not only the final exception.
4. Reproduce with controlled variables.
5. Test the hypothesis and identify the smallest supported cause.
6. Propose a fix plus a regression test.

## Report format
- Verdict / primary cause (or unresolved)
- Evidence (1–3 strongest facts)
- Impact and scope
- Confidence and alternative hypotheses
- Corrective action / owner
- Regression validation and linked evidence

Never invent evidence or expose secrets/PII. Mark uncertain conclusions explicitly.
