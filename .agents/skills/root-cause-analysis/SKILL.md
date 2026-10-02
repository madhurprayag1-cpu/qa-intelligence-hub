---
name: root-cause-analysis
description: Automated log parsing, error signature extraction, root-cause categorization, and code fix synthesis.
---

# Skill: Root Cause Analysis (RCA)

## Purpose
Enables autonomous diagnostic agents to inspect application traces, HTTP response errors, and database exception logs to isolate failure mechanisms without hallucination.

## Workflow
1. **Log Normalization**: Strip ephemeral timestamps and session identifiers to extract pure error signatures.
2. **Category Classification**:
   - `AUTHENTICATION_CHALLENGE`: 3D Secure ACS failures, invalid card tokens.
   - `DATABASE_INTEGRITY`: Foreign key violations, connection pool exhaustion.
   - `NETWORK_GATEWAY`: Upstream API timeouts (504, 502), connection resets.
   - `BUSINESS_LOGIC`: Overbooking inventory races, pricing calculation drift.
3. **Remediation Plan**: Formulate actionable code patches and automated regression test steps.
