# QA Intelligence Hub — Release Evidence Report

**Verification date:** 2026-10-16  
**Repository:** [madhurprayag1-cpu/qa-intelligence-hub](https://github.com/madhurprayag1-cpu/qa-intelligence-hub)  
**Verified release baseline SHA:** `3f338cf75a869eb4c2db7f8637d4c6ccd2901a50`  
**CI run:** [#38862214826](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/runs/38862214826)

## Verified CI results

| Check | Result | Evidence |
|---|---:|---|
| Pytest backend suite | 447 passed, 0 failed | CI backend log + JUnit artifact |
| Playwright E2E suite | 82 passed, 0 failed, 0 skipped | CI E2E log + Playwright JSON artifact |
| Total CI test items | 529 passed | 447 backend + 82 E2E; distinct from capability count |
| Backend `PRODUCTION_STRICT` gate | APPROVED | `quality-gate-summary.md` artifact |
| E2E `PRODUCTION_STRICT` gate | APPROVED | `e2e-quality-gate-summary.md` artifact |
| DAST | 5/5 probes passed; 0 vulnerabilities | `security-dast-report.json` artifact |
| Frontend | Passed | CI frontend job |
| Revision-bound checkpoint | Passed | CI checkpoint job |

## Production verification (read-only, 2026-10-16)

The following endpoints returned HTTP 200: `/`, `/health`, `/qa/release/serving-revision`, `/openapi.json`, `/docs`, `/qa/catalog/summary`, `/qa/layers?include_all=true`, `/qa/ai/providers/status`, and `/qa/production/incidents?status=OPEN`.

The live serving-revision endpoint returned `5779a51686f7a73f1d5d479b74b7bf68d0728d92`, matching the READY Vercel production deployment. The open-incidents endpoint returned zero incidents. No mutating production requests were made.

## Count reconciliation

- **492:** current capability catalog entries across 11 catalog layers.
- **529:** CI test items in the verified run (447 Pytest + 82 Playwright).
- **426:** historical Test Explorer snapshot `RUN-AUTO-20261007-115444`, tied to commit `27848c25e9a88f17e6925b3e63c4d1032b1bc697`; it is not the current CI run and must not be represented as such.

The Test Explorer endpoint still reads its committed historical evidence snapshot. The API now returns snapshot and serving SHAs, and the UI explicitly labels the snapshot as historical when they differ. The endpoint `/qa/test-runner/execute` emits simulated assertions and is not valid evidence for a real regression run. Current release execution evidence is taken from the revision-bound CI artifacts; the historical 426-test snapshot is retained but not misrepresented as current.

## AI-provider decision

Keep `HERMETIC_OFFLINE_MOCK` as the current production/CI mode. This is consistent with deterministic, provider-independent tests and avoids adding external credentials or non-deterministic provider dependencies to this release. Gemini, Claude, and OpenAI are not configured; live-provider integration and provider-specific evaluations are out of scope for this release and must not be claimed as passed.

## Final status

**PASS — final release scope verified.** Main CI run #38862214826 passed 447 backend tests and 82 Playwright E2E tests; backend, frontend, E2E, and checkpoint jobs passed. Both strict quality gates were approved, DAST found 0 vulnerabilities, the deployed serving SHA matched the verified release baseline, and the read-only production smoke checks passed. The historical Test Explorer snapshot is explicitly labelled by API metadata and UI warning; it is not claimed as the current run.
