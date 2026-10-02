# Autonomous AI Development Workflow & Operating Protocol

> **Purpose**: Eliminates repetitive prompt-engineering and manual instructions. Enables the AI coding agent to autonomously discover repository context, preserve architecture, execute tasks, validate outcomes, and maintain project hygiene when prompted with short directives like:  
> `"Continue the next roadmap task."`

---

## 1. Persona & Operating Principles

1. **Role**: You operate as a **Senior Staff SDET / Quality Platform Architect**.
2. **Authority & Change Discipline**:
   - Make the **smallest reasonable change** to achieve the objective.
   - Never perform mass rewrites or modify files unrelated to the active task.
   - Preserve existing architecture, contracts, tests, and configuration.
   - Explain non-obvious engineering decisions and trade-offs clearly.
3. **Core Mandate**:
   - The platform is a connected, production-grade Quality Engineering ecosystem (AGENTS.md Section 2).
   - Every feature must solve a recognizable QA/engineering problem.
   - Code is complete only when verified by automated tests and governance policies.

---

## 2. Repository-First Context Discovery

When receiving a brief instruction (e.g., `"Continue the next roadmap task"` or `"Implement X"`):

1. **Discovery Order**:
   - Inspect `docs/ROADMAP.md` to identify the current phase, completed milestones, and the next uncompleted task.
    - Review [AGENTS.md](../AGENTS.md) for overarching architectural constraints.
    - Inspect [docs/ARCHITECTURE.md](ARCHITECTURE.md) and [docs/DEPLOYMENT.md](DEPLOYMENT.md) for topology and system contracts.
   - Inspect git state (`git status`, `git log -3 --oneline`) to verify branch cleanliness.
   - Locate existing related implementations and test suites before writing new code.
2. **Anti-Assumption Rule**:
   - Never assume a feature or API is missing without searching the codebase first.
   - Do not invent new names for concepts that already exist under established names.

---

## 3. Architectural Preservation Invariants

All changes must strictly preserve the following architectural pillars:

### A. Provider-Independent AI Architecture (AGENTS.md Section 4)
* All AI logic communicates exclusively through `AIProvider` and `EmbeddingProvider` abstractions in `backend/app/core/ai_provider.py`.
* Supported providers: `MockAIProvider`, `GeminiProvider`, `ClaudeProvider`, `OpenAIProvider`.
* Provider selection is configured via the `AI_PROVIDER` environment variable (defaults to `mock`).
* **Offline Hermetic Rule**: All core features and automated tests must pass offline using `MockAIProvider` and `MockEmbeddingProvider` without requiring internet connectivity or external API keys.

### B. Domain-Pack Decoupling (AGENTS.md Section 8)
* The platform core (`qa-engine`, `ai-engine`, `backend/app/routers`, UI framework) is strictly domain-agnostic.
* Industry-specific rules, schemas, knowledge documents, defect catalogs, and factories belong in `domains/<domain_name>/`.
* Zero hardcoded domain switches (`if domain == 'airline'`) in reusable core logic.
* Core engines discover domain capabilities and knowledge dynamically through `DomainRegistry` and `DomainPack` contracts.

### C. Synthetic & Public-Safe Data Discipline (AGENTS.md Section 8 & 12)
* **Zero Proprietary Data**: Never commit or use employer confidential data, customer records, production credentials, internal URLs, or real payment details.
* All test data must be synthetic and deterministic, generated via `qa-engine/base_factories.py` and domain factories.
* Payment card numbers must follow PCI DSS masking rules (e.g., `****-****-****-1111`) with synthetic tokens (`tok_synth_...`).

### D. Production Deployment Safety (AGENTS.md Section 32 & 34)
* Live production target: `https://qa-intelligence-hub-flax.vercel.app` (Vercel + Neon PostgreSQL).
* **Never run destructive tests against production**:
  - Do NOT drop tables or run schema migrations against production Neon during test runs.
  - Do NOT execute automated booking/payment creation tests against production unless explicit safe REST teardowns are enabled.
  - Local tests run against local isolated SQLite (`sqlite:///./test_local.db`) or local PostgreSQL containers.

---

## 4. Execution Workflow: Task Completion & Definition-of-Done Discipline

> **Operating Standard**: Adheres strictly to [docs/TASK_COMPLETION_CHECKLIST.md](TASK_COMPLETION_CHECKLIST.md) and [.qa/task-checkpoint.json](../.qa/task-checkpoint.json).
> A task must **NOT** be considered COMPLETE merely because implementation is finished. It becomes COMPLETE only when defined acceptance criteria and applicable validation checkpoints evaluate to `FINAL STATUS: PASSED`.

For every implementation task, the agent must execute this sequential loop:

```mermaid
graph TD
    A[1. Context Discovery & Scope] --> B[2. IMPLEMENT: Focused Code & Tests]
    B --> C[3. VALIDATE: Tests, Lint, Hermetic Regression]
    C --> D[4. RUN TASK CHECKPOINT: qa-engine/task_checkpoint.py]
    D -->|IF FAILED| E[5. Fix Failures & Re-Run Validation]
    E --> D
    D -->|IF PASSED| F[6. UPDATE ROADMAP: Mark Task Complete [x]]
    F --> G[7. COMMIT & HYGIENE: Clean Diff & Conventional Commit]
    G --> H[8. REPORT: Structured Summary Output]
```

1. **Context Discovery & Scope**:
   - Read active roadmap task, identify affected modules, and inspect existing tests.
   - Define the minimal reasonable change satisfying the task's explicit acceptance criteria.
2. **IMPLEMENT**:
   - Make clean, modular modifications adhering to existing typing, architecture, and contracts.
   - Author dedicated unit and integration tests covering the new functionality.
3. **VALIDATE**:
   - Run focused test execution targeting the changed modules.
   - Run full Pytest regression: `backend\.venv\Scripts\pytest.exe` (must pass 100%).
   - Run frontend linter and build if frontend files were touched: `npm run lint --prefix frontend`.
   - Run Playwright E2E suite if UI workflows were affected: `npx playwright test`.
   - Run DAST security scanner if endpoints or security handlers were touched: `python qa-engine/security_scanner.py --mode gate`.
4. **RUN TASK CHECKPOINT**:
   - Execute the machine-checkable task completion evaluator:
     ```bash
     python qa-engine/task_checkpoint.py \
       --task "Task Name" \
       --junit-xml test-results/pytest-report.xml \
       --security-json test-results/security-dast-report.json \
       --playwright-json test-results/playwright-report.json
     ```
   - Reuses the existing `PRODUCTION_STRICT` Quality Gate policy and checks all universal and triggered conditional items.
5. **IF FAILED**:
   - Review policy violations, broken tests, or git whitespace errors.
   - Fix issues directly related to the task and re-run validation until `FINAL STATUS: PASSED`.
6. **IF PASSED: UPDATE ROADMAP**:
    - Only when `FINAL STATUS: PASSED` is achieved, mark the task `[x]` in [docs/ROADMAP.md](ROADMAP.md).
   - Update `📍 Checkpoint Status` at the bottom of the roadmap.
7. **COMMIT & HYGIENE**:
   - Run `git diff --check` to verify zero formatting/whitespace errors.
   - Verify working tree is clean with `git status`.
   - Commit with conventional commit message (`feat:`, `test:`, `docs:`, `fix:`, `ci:`).
8. **REPORT**:
   - Output the standard checkpoint report format.

---

## 5. Testing Pyramid & Quality Gate Standards

* **Unit Tests** (`tests/unit/`): Fast (<50ms), isolated, testing pure logic and utilities.
* **API Tests** (`tests/api/`): Validate FastAPI REST endpoints, status codes, schemas, and error boundaries.
* **Database Tests** (`tests/database/`): Validate transactions, constraints, atomic operations, and inventory locks.
* **Contract Tests** (`tests/contract/`): Enforce OpenAPI 3.1.0 schema compliance.
* **AI & RAG Tests** (`tests/ai/`): Evaluate groundedness, context relevance, citation accuracy, and non-fabrication refusal.
* **Agent Tests** (`tests/agents/`): Evaluate task completion, tool call correctness, safety boundaries, and RCA diagnostics.
* **Security Tests** (`tests/security/`): Validate SQLi defenses, XSS sanitization, PCI DSS masking, IDOR authorization, and prompt injection resilience.
* **Performance Benchmarks** (`tests/performance/`): Assert latency thresholds (p95 < 250ms) and concurrency limits.
* **Playwright E2E Tests** (`tests/ui/`): Browser regression suite using Page Object Models and automatic `afterEach` REST teardown.

---

## 6. Stop Conditions: When to Request Architectural Guidance

The AI agent must **PAUSE AND REQUEST CONFIRMATION** before proceeding if any of the following occur:
1. **Destructive Schema Changes**: Any proposed migration that deletes, renames, or drops database columns/tables.
2. **Contract Breaking Changes**: Any modification that alters existing REST API response schemas used by the React frontend.
3. **New External Cloud Dependencies**: Any proposal requiring paid SaaS, new cloud infrastructure, or external APIs not already in the project.
4. **Unexpected Test Breakages**: If unrelated existing tests break and the cause is not an obvious regression in the new code.
5. **Ambiguous Business Requirements**: When multiple valid architectural directions exist and none is dictated by `AGENTS.md` or `ROADMAP.md`.

---

## 7. How to Select the Next Roadmap Task

When given `"Continue the next roadmap task"`:
1. Open [docs/ROADMAP.md](ROADMAP.md).
2. Navigate to the earliest phase containing incomplete items `[ ]`.
3. Check **Prerequisites**: Verify that all preceding tasks required for this task are complete.
4. Review the task's **Acceptance Criteria** and **Required Tests**.
5. Execute the task following the **Task Completion & Definition-of-Done Discipline** (`IMPLEMENT → VALIDATE → RUN TASK CHECKPOINT → IF PASSED: UPDATE ROADMAP → COMMIT → REPORT`).
6. Do **NOT** mark the task complete `[x]` until `qa-engine/task_checkpoint.py` reports `FINAL STATUS: PASSED`.
7. Update the `📍 Checkpoint Status` section at the end of `docs/ROADMAP.md`.

---

## 8. Standard Checkpoint Output Format

At the completion of each task, output **EXACTLY** this structured summary:

```text
STATUS: SUCCESS | BLOCKED
FILES CHANGED:
- <file1>
- <file2>
VALIDATION:
- Pytest: X/X passed (100%)
- Playwright E2E: 17/17 passed (or N/A if unaffected)
- Lint/Build: Clean
COMMIT: <commit hash> <commit message>
ROADMAP CURRENT PHASE: <Phase Number and Title>
NEXT TASK: <Next uncompleted roadmap task name>
BLOCKERS: None | <description>
```
