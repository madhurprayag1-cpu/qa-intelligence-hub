# System Context — QA Intelligence Hub

## Purpose
Provide an auditable quality-engineering platform for UI/API/database tests, security checks, AI/RAG evaluation, release evidence, and risk-based release decisions.

## Architecture and stack
- Frontend: React 19, TypeScript, Vite.
- API: Python 3.13, FastAPI, Pydantic; PostgreSQL in CI.
- UI automation: Playwright Test (TypeScript); API/backend tests: pytest.
- CI: GitHub Actions; frontend hosting/deployment: Vercel.
- AI: provider abstraction; deterministic `HERMETIC_OFFLINE_MOCK` is the documented default unless explicitly configured otherwise.
- Existing quality-gate and evidence tooling is authoritative; do not create duplicate systems without an approved reason.

## Engineering principles
1. Inspect existing patterns before changing architecture.
2. Keep business logic modular and contracts explicit.
3. Preserve backward compatibility unless a migration is deliberate and tested.
4. Use reproducible, deterministic tests; isolate external services.
5. Evidence must identify the source revision and execution environment.
6. Never claim a test, scan, deployment, or compliance check passed without current evidence.

## AI responsibilities
AI may propose test cases, analyze sanitized evidence, explain likely causes, and draft patches. Generated changes must be validated by deterministic checks and reviewed before merge. AI output is advisory, not proof.

## Change workflow
Audit → scoped branch → minimal change → tests and security checks → review → merge through protected process → verify deployed revision. Never deploy from an unverified worktree.
