# Public API Security Inventory

**Scope:** all HTTP operations exposed by the production OpenAPI document at the time of this audit (2026-10-16). This is a route-level policy inventory, not a penetration-test attestation.

**Policy:** the recruiter-facing web app, public reference catalogs, synthetic QA catalog/evidence, and non-persistent analysis actions remain publicly reachable. In production, the middleware denies all `POST`, `PUT`, `PATCH`, and `DELETE` operations unless the exact `POST` path is in `PUBLIC_READ_ONLY_POST_PATHS`. The listed public POSTs are rate-limited per process. Sensitive record reads return `404`. Authentication-required endpoints still enforce their dependencies. Test-only defect injection and caller-supplied role headers are ignored in production.

**Important limit:** the in-process limiter is defense-in-depth only. Vercel serverless instances do not share memory; configure and verify Vercel Firewall edge rate limits before treating rate limiting as globally enforced.

## Endpoint-by-endpoint inventory

| Method | Path | Classification | Production policy / rationale |
|---|---|---|---|
| GET | `/health` | Public read-only | Health status only; no credentials or database contents |
| POST | `/auth/login` | Privileged / disabled | Demo-password authentication disabled in production; not in public POST allowlist |
| GET | `/auth/demo-users` | Public read-only / disabled | Returns 404 in production |
| POST | `/auth/demo-session` | Public action | Issues a synthetic passenger token only; rate-limited; production write operations remain blocked |
| GET | `/auth/me` | Authenticated read | Requires a valid signed bearer token |
| GET | `/airlines` | Public read-only | Public reference catalog |
| GET | `/airports` | Public read-only | Public reference catalog |
| GET | `/flights/search` | Public read-only | Search alias; test defect flags ignored in production |
| GET | `/flights` | Public read-only | Active flight catalog |
| GET | `/search/flights` | Public read-only | Search synthetic flight data; test defect flags ignored in production |
| GET | `/bookings/ancillaries/catalog` | Public read-only | Static ancillary catalog |
| POST | `/bookings` | Privileged / disabled | Writes booking and seat inventory; denied in production |
| GET | `/bookings/{booking_id}` | Sensitive read / disabled | May expose passenger data; returns 404 in production |
| GET | `/bookings/reference/{reference}` | Sensitive read / disabled | May expose passenger data; returns 404 in production |
| POST | `/bookings/{booking_id}/cancel` | Privileged / disabled | Changes booking, inventory and refund state; denied |
| POST | `/payments` | Privileged / disabled | Writes payment and booking state; denied |
| GET | `/payments/{booking_id}` | Sensitive read / disabled | May expose payment metadata; returns 404 in production |
| GET | `/ai/providers` | Public read-only | Provider mode/status metadata only |
| POST | `/ai/evaluate/groundedness` | Public action | Stateless evaluation; rate-limited |
| GET | `/ai/rag/knowledge` | Public read-only | Returns index counts/domain metadata only |
| POST | `/ai/rag/knowledge` | Privileged / disabled | Mutates the shared RAG index; denied |
| POST | `/ai/rag/query` | Public action | Query-only against synthetic indexed knowledge; rate-limited |
| POST | `/ai/rca` | Public action | Stateless analysis; rate-limited |
| POST | `/ai/rca/remediate` | Privileged / disabled | Remediation operation not approved for anonymous production use; denied |
| POST | `/ai/security/audit` | Privileged / disabled | Security audit execution not in public allowlist; denied |
| POST | `/ai/security/scan-suite` | Privileged / disabled | Potentially expensive scan execution; denied |
| GET | `/defects` | Public read-only | Documents synthetic test defects; defect activation is disabled in production |
| GET | `/defects/{defect_id}` | Public read-only | Documents synthetic test defects; no activation |
| GET | `/quality-gate/policies` | Public read-only | Static quality policy catalog |
| POST | `/quality-gate/evaluate` | Privileged / disabled | Persists a quality-gate audit record; denied |
| GET | `/quality-gate/runs` | Public read-only | Historical synthetic QA telemetry |
| GET | `/quality-gate/runs/{run_id}` | Public read-only | Historical synthetic QA telemetry |
| POST | `/quality-gate/override` | Privileged / disabled | Release sign-off override; denied in production regardless of caller headers |
| GET | `/qa/layers` | Public read-only | Static architecture/catalog information |
| POST | `/qa/regression/impact` | Public action | Stateless diff-impact analysis; rate-limited |
| POST | `/qa/test-runner/execute` | Privileged / disabled | Executes test workloads; denied to anonymous production traffic |
| POST | `/qa/requirements/analyze` | Privileged / disabled | Persists requirement traceability; denied |
| GET | `/qa/requirements/{requirement_id}` | Sensitive read / disabled | May return user-submitted requirement content; returns 404 in production |
| POST | `/qa/requirements/{requirement_id}/engineering-plan` | Privileged / disabled | Mutating/plan-generation route not allowlisted; denied |
| GET | `/qa/requirements/{requirement_id}/test-plan` | Sensitive read / disabled | May return user-submitted requirement content; returns 404 in production |
| POST | `/qa/production/observations` | Privileged / disabled | Persists operational observations; denied |
| GET | `/qa/production/incidents` | Sensitive read / disabled | Operational incident data; returns 404 in production |
| GET | `/qa/production/incidents/{incident_id}` | Sensitive read / disabled | Operational incident data; returns 404 in production |
| POST | `/qa/production/incidents/{incident_id}/resolve` | Privileged / disabled | Changes incident state; denied |
| POST | `/qa/reporting/release-report` | Public action | Stateless report synthesis; rate-limited |
| POST | `/qa/self-heal/selector` | Public action | Stateless locator recommendation; rate-limited |
| POST | `/qa/performance/stress-test` | Privileged / disabled | Generates load; denied to anonymous production traffic |
| GET | `/qa/runtime/metrics` | Sensitive read / disabled | Internal process telemetry; returns 404 in production |
| GET | `/qa/ai/providers/status` | Public read-only | Provider mode/status; no secrets returned |
| GET | `/qa/domain` | Public read-only | Active synthetic demo domain |
| POST | `/qa/domain/switch` | Privileged / disabled | Changes shared domain state; denied |
| POST | `/qa/domain/reset` | Privileged / disabled | Resets shared domain state; denied |
| GET | `/qa/catalog` | Public read-only | Public capability catalog |
| GET | `/qa/catalog/summary` | Public read-only | Public catalog summary |
| GET | `/qa/evidence/latest` | Public read-only | Public synthetic QA evidence |
| POST | `/qa/orchestrator/run` | Privileged / disabled | Runs orchestration and may persist state; denied |
| GET | `/qa/capabilities` | Public read-only | Public capability catalog |
| GET | `/qa/capabilities/{capability_id}` | Public read-only | Public capability detail |
| GET | `/qa/tests` | Public read-only | Public test evidence; historical snapshots are labelled |
| GET | `/qa/tests/{test_id}` | Public read-only | Public test evidence; historical snapshots are labelled |
| GET | `/qa/runs` | Public read-only | Public run evidence |
| GET | `/qa/runs/{run_id}` | Public read-only | Public run evidence |
| GET | `/qa/runs/{run_id}/tests` | Public read-only | Public run evidence |
| GET | `/qa/release/serving-revision` | Public read-only | Exposes serving revision/environment for evidence correlation |
| POST | `/healthcare/patients` | Privileged / disabled | Writes clinical-style records; denied |
| GET | `/healthcare/patients` | Sensitive read / disabled | Returns 404 in production |
| GET | `/healthcare/patients/{patient_id}` | Sensitive read / disabled | Returns 404 in production |
| GET | `/healthcare/practitioners` | Public read-only | Synthetic public catalog only |
| POST | `/healthcare/observations` | Privileged / disabled | Writes clinical-style observations; denied |
| GET | `/healthcare/observations` | Sensitive read / disabled | Returns 404 in production |
| POST | `/healthcare/appointments` | Privileged / disabled | Writes appointment records; denied |
| GET | `/healthcare/appointments` | Sensitive read / disabled | Returns 404 in production |
| POST | `/healthcare/dosage/calculate` | Public action | Stateless synthetic calculation; rate-limited |
| GET | `/healthcare/defects` | Public read-only | Defect documentation only; production injection disabled |
| POST | `/fintech/accounts` | Privileged / disabled | Writes account records; denied |
| GET | `/fintech/accounts` | Sensitive read / disabled | Returns 404 in production |
| GET | `/fintech/accounts/{account_id}` | Sensitive read / disabled | Returns 404 in production |
| GET | `/fintech/transactions/{account_id}` | Sensitive read / disabled | Returns 404 in production |
| POST | `/fintech/transfers` | Privileged / disabled | Financial transfer simulation may persist state; denied |
| POST | `/fintech/transfers/swift` | Privileged / disabled | Financial transfer simulation may persist state; denied |
| POST | `/fintech/kyc/verify` | Public action | Stateless synthetic evaluation; rate-limited |
| POST | `/fintech/fraud/evaluate` | Public action | Stateless synthetic evaluation; rate-limited; defect flags stripped |
| POST | `/fintech/exchange/calculate` | Public action | Stateless calculation; rate-limited; defect flags stripped |
| GET | `/fintech/defects` | Public read-only | Defect documentation only |
| GET | `/ecommerce/products` | Public read-only | Public product catalog |
| POST | `/ecommerce/products` | Privileged / disabled | Writes product catalog; denied |
| POST | `/ecommerce/cart/validate` | Public action | Stateless calculation; rate-limited |
| POST | `/ecommerce/checkout` | Privileged / disabled | Creates orders and changes state; denied |
| GET | `/ecommerce/orders` | Sensitive read / disabled | Returns 404 in production |
| GET | `/ecommerce/orders/{order_id}` | Sensitive read / disabled | Returns 404 in production |
| PUT | `/ecommerce/orders/{order_id}/status` | Privileged / disabled | Changes order state; denied |
| POST | `/ecommerce/refunds` | Privileged / disabled | Creates refund records; denied |
| GET | `/ecommerce/defects` | Public read-only | Defect documentation only |
| POST | `/telecom/reset` | Privileged / disabled | Resets shared synthetic state; denied |
| GET | `/telecom/plans` | Public read-only | Public plan catalog |
| POST | `/telecom/subscribers` | Privileged / disabled | Creates subscriber records; denied |
| GET | `/telecom/subscribers/{msisdn}` | Sensitive read / disabled | Returns 404 in production |
| GET | `/telecom/subscribers/{msisdn}/cdrs` | Sensitive read / disabled | Returns 404 in production |
| POST | `/telecom/subscribers/{msisdn}/status` | Privileged / disabled | Changes subscriber status; denied |
| POST | `/telecom/subscribers/{msisdn}/sim-swap` | Privileged / disabled | Changes subscriber/SIM state; denied |
| POST | `/telecom/cdr/rate` | Public action | Stateless synthetic rating calculation; rate-limited |

## Controls implemented on the hardening branch

- Production and Vercel Preview writes fail closed except for the exact non-persistent public POST allowlist above.
- Runtime additive DDL is skipped in Vercel Preview and Production; schema changes must run through controlled migrations, important because Preview may share the configured database URL.
- Sensitive booking, payment, healthcare, fintech, ecommerce, telecom, requirement, incident, and runtime-metric reads are denied anonymously.
- Production identity resolution requires a valid bearer token; caller-supplied role and user-ID headers are not trusted.
- Intentional defect injection is disabled in production.
- CORS no longer trusts arbitrary `*.vercel.app` origins and no longer enables credentialed cross-origin requests.
- Bootstrap failures return a generic 503 with a stable error code; tracebacks and import paths are logged server-side only.
- CI adds Bandit, pip-audit, npm audit and Gitleaks, and the checkpoint fails if the security job fails.
- Regression tests cover denied writes, sensitive reads, forged roles, disabled defect injection, CORS, safe public actions and rate-limit responses.

## Remaining deployment gate

The app-level limiter is not a distributed rate limiter. The read-only Vercel Firewall configuration lookup returned `404: Seawall Config not found`, so active edge-level rate-limit rules could not be verified. Before production release, configure and verify Vercel Firewall edge-level rate limits and managed protections in a separately reviewed infrastructure change. This branch does not modify production infrastructure or database contents.
