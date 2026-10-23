# Coding Standards

## General
Follow existing repository conventions; keep changes focused, typed, modular, and reviewable. Avoid duplicated framework layers and speculative abstractions.

## Python
Use type hints for public interfaces, Pydantic for API contracts, explicit exception handling, parameterized database operations, and deterministic pytest fixtures. Do not swallow exceptions or log secrets.

## TypeScript/Playwright
Use strict typing, reusable fixtures/helpers, descriptive test names, component/page abstractions where they reduce duplication, and web-first assertions. Avoid arbitrary sleeps and shared mutable test state.

## Assertions and errors
Assertions must verify business outcomes, not merely absence of exceptions or HTTP 200. Error handling must preserve diagnostic context without exposing credentials or private data.

## Review checklist
Correctness; readability; test coverage; security/privacy; compatibility/migrations; determinism; observability; documentation; performance; and rollback/recovery. Run the narrowest relevant checks and full required CI before merge.
