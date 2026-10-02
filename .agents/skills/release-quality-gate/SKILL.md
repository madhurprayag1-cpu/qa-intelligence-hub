---
name: release-quality-gate
description: Multi-signal release governance evaluating test passes, critical defects, security findings, and AI metrics.
---

# Skill: Release Quality Gate

## Purpose
Enforces automated gatekeeping for CI/CD pipelines, preventing risky releases from entering production environments.

## Signals
1. **Test Pass Rate**: Unit, API, and UI automated suites must achieve configured pass thresholds (100% for strict).
2. **Defect Severity**: Zero unresolved critical (`CRITICAL` / `BLOCKER`) defects permitted.
3. **Security Vulnerabilities**: Zero high-severity findings (SQLi, IDOR, sensitive card data exposure).
4. **AI/RAG Evaluation**: Groundedness and accuracy scores must satisfy minimum threshold ($\ge 0.85$).
5. **Contract Conformance**: Schema validation violations must be zero.
