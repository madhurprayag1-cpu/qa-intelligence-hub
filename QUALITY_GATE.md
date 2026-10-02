# QA Intelligence Hub — Authoritative Quality Gate

This document is the mandatory execution and verification contract for every meaningful implementation, bug fix, milestone, release, and deployment in this repository. It defines **how work is assessed, validated, evidenced, and completed**; it does not replace the ownership of other project documents.

## 1. Authority and document ownership

Follow this hierarchy and preserve each document's purpose:

1. [`AGENTS.md`](AGENTS.md) is the highest-level engineering and agent behavior contract. If this gate appears to conflict with it, follow `AGENTS.md` and resolve the discrepancy rather than silently changing either rule.
2. **This file** defines the mandatory execution and quality gate, including evidence, failure handling, production verification, and completion criteria.
3. [`README.md`](README.md) owns the user-facing overview, setup, capabilities, and project status.
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) owns system architecture and design decisions.
5. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) owns deployment infrastructure, environment configuration, migrations, operational procedures, and deployment smoke-test instructions.
6. [`docs/domain-extension-guide.md`](docs/domain-extension-guide.md) owns domain-pack extension architecture and its implementation guide.
7. [`docs/ROADMAP.md`](docs/ROADMAP.md) owns planned work, milestones, and project progression.
8. [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md) owns the AI-assisted development workflow and standard task report format.
9. [`docs/TASK_COMPLETION_CHECKLIST.md`](docs/TASK_COMPLETION_CHECKLIST.md) owns task-level universal and conditional checklist details.
10. [`.qa/task-checkpoint.json`](.qa/task-checkpoint.json) owns machine-readable checkpoint policy and configured checks; [`qa-engine/task_checkpoint.py`](qa-engine/task_checkpoint.py) owns its evaluator and executable checkpoint behavior.

Consult the owning document for detailed instructions. This gate consolidates when and why those checks apply; it does not duplicate or supersede their implementation-specific details. Keep documentation consistent with actual code and configuration.

## 2. Applicability and scope

Apply this gate to every meaningful change. Determine applicability from changed files, acceptance criteria, affected contracts, and risk—not from a desire to skip an inconvenient check. Run focused checks first, then all affected conditional checks, then the applicable full gate. Documentation-only changes do not require unrelated browser or application test suites, but still require review, link/command accuracy checks as applicable, and Git hygiene.

Before work, inspect repository instructions, the relevant implementation and tests, the roadmap/checkpoint requirements when applicable, and the worktree. Establish the requested scope, acceptance criteria, affected components, baseline failures, and a safe validation plan. Do not overwrite an existing target or alter unrelated user work.

## 3. Mandatory execution loop

Use this sequence for meaningful implementation, defect remediation, and milestone work:

1. **Assess** requirements, scope, acceptance criteria, architecture, risk, worktree, and applicable policy.
2. **Identify failures** by reproducing or confirming the reported behavior and capturing relevant evidence.
3. **Diagnose root cause**; distinguish cause from symptoms and record the reasoning in task evidence.
4. **Implement the minimal correct fix** consistent with existing contracts and architecture.
5. **Run targeted validation** for the changed behavior, including a regression assertion for a fixed defect.
6. **Run affected quality gates** selected by changed components and risk.
7. **Run the full required quality gate** for the task or milestone, including the checkpoint evaluator where task completion policy requires it.
8. **Review/update documentation** when behavior, commands, architecture, security posture, deployment, or project status changes.
9. **Commit only when authorized** and all required checks pass; use the repository's conventional commit guidance.
10. **Deploy only when explicitly authorized** and only after pre-deployment checks pass.
11. **Verify the deployment** using production-safe smoke and security checks when deployment is in scope.
12. **Record checkpoint/evidence**, report final status, and continue to the next in-scope milestone when authorized.

Finding a defect is not by itself a reason to terminate the task. Continue through diagnosis, a minimal correct fix, validation, and affected regression checks. Pause and request a human decision only for the stop conditions in Section 12.

## 4. Requirements, design, and code quality

- Trace implementation and tests to explicit requirements and acceptance criteria. Do not invent material business behavior where it is undefined.
- Inspect existing patterns before changing behavior. Prefer the smallest maintainable change; avoid unrelated refactoring and unnecessary framework or infrastructure changes.
- Preserve backward compatibility and public API contracts unless a change is intentional, specified, tested, and documented.
- Keep code typed, modular, readable, and testable. Include appropriate validation, structured error handling, and observable diagnostics; do not expose internal exceptions or sensitive data.
- Verify that generated or AI-assisted code, dependency choices, external API contracts, configuration, and model/provider assumptions are real and validated. Do not add hallucinated dependencies.
- Treat intentional defects as documented, controlled, and reproducible test scenarios; do not accidentally mask them or confuse them with unresolved product defects.

## 5. Architecture and domain boundaries

- Preserve the connected-system contracts and modular architecture documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); do not introduce unnecessary services or framework changes.
- Keep reusable QA platform/core behavior domain-independent. Put domain-specific business rules, schemas, data, and workflows in domain packs; follow [`docs/domain-extension-guide.md`](docs/domain-extension-guide.md). Do not add domain-specific conditionals to shared core as a shortcut.
- Preserve provider-independent AI interfaces. Provider-specific behavior belongs behind those interfaces; core functionality and tests should retain the documented offline/mock path.
- Preserve existing public REST, UI, persistence, and agent/tool contracts unless a contract change is explicitly intended and verified across consumers.
- Keep agent actions bounded by explicit tools, permissions, and contracts; verify auditability, traceability, and unauthorized-operation denial.

## 6. Component and test gates

Tests are quality contracts. Never weaken assertions, delete tests, skip failing tests, disable gates, or suppress errors merely to obtain a passing result. Select tests from the current repository configuration and checkpoint policy; documented counts are historical evidence, not a substitute for running tests or an automatic threshold.

### 6.1 Test execution

- Run focused tests for changed behavior first, then relevant regression suites, then the applicable full suite.
- Run the full hermetic pytest regression and applicable strict quality/checkpoint evaluation for task or milestone completion as required by [`docs/TASK_COMPLETION_CHECKLIST.md`](docs/TASK_COMPLETION_CHECKLIST.md) and [`.qa/task-checkpoint.json`](.qa/task-checkpoint.json).
- Run Playwright UI tests when frontend, browser workflows, UI tests, or Playwright configuration are affected; use the established page objects, fixtures, and deterministic test data.
- Run API and OpenAPI contract checks when routes, schemas, API behavior, or contract tests change. Verify status, headers, schema, business rules, error behavior, and relevant persistence.
- Run database invariants and migration checks when models, database access, schemas, or migrations change.
- Run relevant AI/RAG evaluation when retrieval, prompts, models/providers, knowledge, embeddings, or AI behavior change. Evaluate retrieval and generated answers, including relevance, groundedness, citations, filtering/isolation, refusal/safety, and appropriate configured thresholds; a successful HTTP response alone is insufficient.
- Run agent evaluations when agent logic or tools change, including task outcome, tool choice/arguments, boundaries, authorization, recovery, and traceability.
- Run security and performance checks when triggered by changed components or risk. Do not infer that a scanner's clean baseline proves every security property.
- For unrelated conditional suites, record **not applicable** with the scope-based reason; never call a failed or unrun required check passed.

### 6.2 Required quality domains

For each change, assess and test applicable areas across requirements/scope; architecture; code quality; backend; frontend; API; database and migrations; synthetic test data; UI, API, database, contract, and regression testing; security; authentication, authorization, and tenant isolation; secrets and dependency security; DAST and adversarial testing; AI, RAG, LLM evaluation, and agentic workflows; domain plugins; performance and scalability; observability, logging, and monitoring; CI/CD; deployment and production smoke testing; rollback readiness; documentation; reproducibility; and Git hygiene.

An area is not silently exempt because it is absent from a particular change. Mark it not applicable when genuinely unaffected, and investigate any risk that crosses component boundaries.

### 6.3 Test data and reproducibility

- Use synthetic, non-confidential data; use deterministic factories/fixtures where appropriate.
- Keep tests independent, environment-safe, and isolated from production data/services. Do not direct test, seed, migration, or teardown commands at a production database.
- Record environment prerequisites and use project-supported commands. A missing local tool or unavailable external service is a blocker for that check, not a pass; use documented hermetic alternatives where available.
- For flaky tests, investigate and classify the cause. Do not simply increase timeouts, remove assertions, or retry until green without evidence and an explicit, justified policy.

## 7. Security gate

Assess security on every meaningful change and perform deeper checks when the changed surface or risk warrants them. At minimum consider:

- Authentication and authorization: missing, invalid, expired, and insufficient-privilege credentials; role boundaries and server-authoritative identity.
- Tenant/object isolation: cross-user and cross-tenant read/write access, including identifier manipulation and privileged paths.
- Secret exposure: source, configuration, logs, API responses, build artifacts, and Git history/diff; never add secrets or real credentials.
- Insecure defaults and production configuration: debug behavior, development/demo identity, environment settings, CORS, and fail-closed safeguards.
- Input validation and injection: SQL/command/template injection, XSS, unsafe deserialization, and relevant request/file/document payloads.
- Dependency risk: new or changed dependencies and applicable repository security checks.
- DAST/adversarial risks, including prompt injection and unsafe agent/tool use where relevant.
- Sensitive-data handling, redaction, audit logs, and access controls appropriate to the domain.

Required security checks must pass with no unresolved findings that violate the applicable policy. Report accepted residual risks explicitly; do not hide, suppress, or relabel findings to pass a gate.

## 8. Database and migration gate

- PostgreSQL compatibility is required; SQLite-only success is not proof of production database compatibility.
- Validate migration ordering and upgrade behavior against an isolated disposable database. Validate downgrade/recovery behavior when applicable and safe.
- Make production migrations explicit, reviewable, and compatible with the required deployment sequence. Do not run production migrations as an incidental test or seed action.
- No unapproved destructive migration, irreversible data change, production data mutation, or production schema operation is permitted. Request a human decision where authorization or reversibility is uncertain.
- Verify relevant constraints, indexes, foreign keys, transactions, and database invariants. Preserve forward compatibility when required by rollout strategy.

Detailed migration and operational procedures belong to [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## 9. AI, RAG, and agent gate

- Keep provider/model selection configurable behind the documented provider abstractions; verify external provider API contracts and configuration when changed.
- Validate AI-generated outputs instead of treating them as ground truth. Use deterministic assertions where suitable and rubric/metric evaluation where appropriate; do not depend only on exact-string matches.
- Evaluate both RAG retrieval and generation. Verify document/domain/tenant filtering, relevance, grounding, citation correctness, unsupported-claim handling, and safe refusal against the applicable configured policy.
- Test agents for permitted tool selection and arguments, authorization, task completion, safety, failure recovery, observability, and traceability. Agents must not gain arbitrary state access.
- Never require live credentials or external provider availability for core hermetic tests where the documented mock/offline path applies. Do not expose provider secrets in evidence or logs.

## 10. CI/CD, deployment, and production verification

### 10.1 Before deployment

Deploy only when deployment is in scope and explicitly authorized. Verify and record:

- Applicable focused, affected, full, security, and release quality gates pass.
- Required migrations have been reviewed and validated on an isolated target-compatible database; the production migration plan is explicit.
- No task-owned tracked changes remain uncommitted when the release procedure requires a committed revision. Check the worktree without altering pre-existing user changes.
- No secrets are committed or exposed; deployment configuration, target environment, production safeguards, and required environment variables are verified.
- The intended commit/source revision and rollback/recovery plan are known where available. Do not claim a deployment is tied to a revision if that cannot be verified.
- Deployment steps match the current infrastructure and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md); do not infer current cloud settings from old documentation alone.

### 10.2 After deployment

When deployment is authorized, perform and record production-safe checks appropriate to the deployment:

- Frontend loads and critical user journey smoke test passes.
- Health endpoint and representative API smoke checks return expected status and safe responses.
- Authentication and authorization behave as intended, including denial of unauthenticated/unauthorized access where required.
- Tenant/object isolation is checked using safe, synthetic identities and non-destructive requests.
- Database connectivity and migration/schema readiness are verified when applicable without destructive operations.
- Expected source revision is confirmed through reliable deployment metadata when available; record explicitly when it is unavailable.
- Monitoring/logging show no relevant deployment errors or sensitive-data exposure; rollback readiness is understood.

Use the exact target URLs and commands from the current deployment configuration/runbook. Do not make live changes or run destructive probes without authorization. A successful build or HTTP 200 alone is not production verification.

## 11. Failure, root cause, and evidence policy

For every failure:

1. Preserve the failing command, output, environment, and reproducible inputs without recording secrets or sensitive data.
2. Reproduce or otherwise confirm the failure when safe and feasible.
3. Identify and document the actual root cause and why the evidence supports it.
4. Implement the smallest correct fix; do not make speculative or unrelated changes.
5. Re-run the original failing check and relevant affected-area regression checks.
6. Re-run all affected gates and the applicable full gate. Continue until passed or a defined stop condition/blocker requires a human decision.

Prohibited responses include weakening/deleting tests, skipping failures, disabling gates, suppressing errors, hiding results, speculative fixes, unrelated refactoring, hardcoded secrets, and unauthorized destructive operations.

For every completed gate, record: command or validation, environment/scope when relevant, result and counts/metrics, associated commit/revision when available, each failure and its root cause, fix and rerun result, not-applicable rationale for conditional checks, and final status. Keep evidence reproducible and free of credentials, tokens, personal data, and other secrets.

## 12. Stop conditions and authorization

Stop the affected operation and request a human decision before proceeding when it involves:

- A destructive production operation, irreversible data change, or unapproved destructive migration.
- A required credential/secret that has not been provided through an approved secure mechanism.
- An ambiguous authentication, authorization, tenant, or other security boundary.
- Conflicting architectural requirements or multiple materially different architecture choices.
- A material requirement that is undefined and cannot safely be inferred from authoritative project documents.
- An action outside the task's authorization, including commit, push, deployment, or live infrastructure mutation when not authorized.

Do not stop merely because an ordinary test or quality check fails: diagnose, fix, validate, and continue as specified in Sections 3 and 11. If an external dependency or environment prevents a required check, report the exact blocker and mark the gate blocked—not passed.

## 13. Documentation, Git, and checkpoint completion

- Documentation must reflect implemented behavior. Verify commands against project configuration or executable behavior; deployment guidance must match current infrastructure. Review architecture/security docs when those concerns change.
- Propagate reusable engineering rules to their proper owner; do not duplicate detailed policies across documents unnecessarily.
- Review the diff for scope, secrets, generated files, and accidental changes. `git diff --check` must pass.
- Respect existing user changes and untracked files. A clean-worktree requirement applies only when it can be met without discarding or altering unrelated user work; report pre-existing worktree items accurately.
- Run `qa-engine/task_checkpoint.py` and satisfy its configured policy whenever the task/milestone completion process requires it. The authoritative machine-readable checks and evaluator behavior are `.qa/task-checkpoint.json` and `qa-engine/task_checkpoint.py`; do not fabricate inputs or evidence to obtain a pass.
- Record/update checkpoint state only when authorized and using the established mechanism. Do not mark roadmap work complete unless the required checkpoint reports `FINAL STATUS: PASSED` and the roadmap owner’s completion rules are met.
- Commit only when authorized, after applicable gates pass. Do not push or deploy unless separately authorized.

A meaningful task or milestone is complete only when implementation and acceptance criteria are complete; applicable tests and quality/security gates pass; architecture and public contracts are preserved or intentionally changed and verified; documentation review is complete; required deployment verification is complete when deployment is in scope; checkpoint/evidence is recorded; and no known in-scope blocker remains. Report blocked or partial work honestly.

## 14. Final report

Report a concise, evidence-based final status: outcome (`PASSED`, `FAILED`, or `BLOCKED`); files changed; checks run with results and counts; checks not applicable or blocked with reasons; root causes/fixes; documentation/checkpoint updates; commit/deployment/source revision only if actually performed and verified; and unresolved risks or blockers. Follow the exact task-report format in [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md) when that workflow applies. Never represent an unrun, unavailable, or unverified check as passed.