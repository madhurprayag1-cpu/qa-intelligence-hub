# Definition of Done

A change is complete only when applicable criteria are satisfied:

- [ ] Requirement, risk, acceptance criteria, and traceability are documented.
- [ ] Implementation follows architecture and coding standards.
- [ ] Positive, negative, boundary, and security tests are added or existing coverage is justified.
- [ ] Targeted tests pass; full required CI passes before merge/release.
- [ ] Lint, build, dependency, secret, and security checks pass according to repository gates.
- [ ] No secrets or sensitive real data are included in code or evidence.
- [ ] Reports and artifacts identify the exact tested revision.
- [ ] Failures, skipped tests, retries, gaps, and approved exceptions are explicit.
- [ ] Documentation and relevant coverage maps are updated.
- [ ] Review/approval and rollback approach are recorded for risky changes.
- [ ] Production deployment SHA and read-only smoke are verified after release, when release is in scope.

A checklist or Markdown lint alone does not satisfy runtime validation. Do not claim completion while a required criterion is unverified.
