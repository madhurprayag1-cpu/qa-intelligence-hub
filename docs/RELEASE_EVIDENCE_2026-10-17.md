# QA Intelligence Hub — Release Evidence Report

**Verification date:** 2026-10-17  
**Repository:** [madhurprayag1-cpu/qa-intelligence-hub](https://github.com/madhurprayag1-cpu/qa-intelligence-hub)  
**Verified application baseline SHA:** `4fc56aabed1bca367a8510768243e1411cbd7bdf`  
**CI run:** [#39054140934](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/runs/39054140934)

## Verified CI results

| Check | Result | Evidence |
|---|---:|---|
| Pytest backend suite | 447 passed, 0 failed | Revision-bound CI backend job and JUnit artifact |
| Playwright E2E suite | 82 passed, 0 failed, 0 skipped | Revision-bound CI E2E job and Playwright artifact |
| Total CI test items | 529 passed | 447 backend + 82 E2E; distinct from capability count |
| Backend `PRODUCTION_STRICT` gate | APPROVED | CI quality-gate summary |
| E2E `PRODUCTION_STRICT` gate | APPROVED | CI E2E quality-gate summary |
| Deterministic offline RAG benchmark | 15/15 passed | CI backend benchmark |
| RAG groundedness | 0.9685 | Deterministic offline benchmark |
| RAG context relevance | 1.00 | Deterministic offline benchmark |
| RAG citation accuracy | 0.90 | Deterministic offline benchmark |
| RAG truthful refusal | 1.00 | Deterministic offline benchmark |
| Scoped DAST | 5/5 probes passed; 0 findings | CI DAST report; scope-limited result, not external certification |
| Frontend | Passed | CI frontend job |
| Revision-bound checkpoint | Passed | CI checkpoint job |

## Production verification (read-only, 2026-10-17)

The following endpoints returned HTTP 200: `/`, `/health`, `/qa/release/serving-revision`, `/openapi.json`, `/docs`, `/qa/catalog/summary`, `/qa/layers?include_all=true`, `/qa/ai/providers/status`, and `/qa/production/incidents?status=OPEN`.

The live serving-revision endpoint returned `4fc56aabed1bca367a8510768243e1411cbd7bdf`, matching the READY Vercel production deployment at verification time. The open-incidents endpoint returned zero incidents. No mutating production requests were made. This is a dated smoke-test result, not continuous monitoring.

## Count reconciliation

- **492:** live capability catalog entries across 11 layers.
- **529:** CI test items in the verified run (447 Pytest + 82 Playwright).
- **426:** historical Test Explorer snapshot `RUN-AUTO-20261007-115444`, tied to commit `27848c25e9a88f17e6925b3e63c4d1032b1bc697`; it is not the current CI run and must not be represented as such.

The Test Explorer's committed snapshot remains historical. Its API compares the snapshot SHA with the serving SHA, and the UI warns when the snapshot is historical or unknown. The simulated `/qa/test-runner/execute` endpoint is not evidence of an actual full regression. Current release execution evidence is in the revision-bound CI run and artifacts. Do not replace the snapshot with aggregate counts or fabricated per-test records; a true Test Explorer refresh must be generated from the actual test-level CI artifacts and validated against the revision being served.

## AI-provider decision

Keep `HERMETIC_OFFLINE_MOCK` as the current production/CI mode. The deterministic benchmark validates mock-mode behavior only. Gemini, Claude, and OpenAI are not configured; live-provider integration and provider-specific evaluations remain out of scope and must not be claimed as passed.

## Main-branch governance

The active `Protect main branch` ruleset requires a pull request, resolved review threads, and successful `backend`, `frontend`, `e2e`, and `checkpoint` status checks. It blocks branch deletion and force-push. It requires zero approving reviews, and the strict up-to-date-branch requirement is disabled. The required checks still have to pass before merge.

## Final status

**PASS — verified application baseline.** CI run #39054140934 passed 447 backend tests and 82 Playwright E2E tests; backend, frontend, E2E, and checkpoint jobs passed. Strict quality gates were approved, the deterministic offline RAG benchmark passed, scoped DAST had zero findings, and the deployment serving SHA matched the verified application baseline. The historical Test Explorer snapshot is not current execution evidence.

The production topology is Vercel + Neon. `render.yaml` is an alternate configuration and Render is not treated as an active production target in this release evidence.
