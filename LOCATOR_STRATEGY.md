# Locator Strategy

## Priority order
1. Accessible role and name.
2. Associated label or placeholder where semantically appropriate.
3. Stable, user-facing text when unique and localization-safe.
4. Explicit test ID such as `data-testid` for otherwise ambiguous controls.
5. CSS based on stable, intentional attributes.
6. XPath only when no maintainable alternative exists.

## Rules
Use Playwright's auto-waiting and web-first assertions. Scope locators to a component/container and assert uniqueness when ambiguity is possible. Avoid generated classes, DOM depth, positional selectors, brittle XPath, and arbitrary sleeps.

## Recovery
On locator failure, capture sanitized evidence and inspect DOM/accessibility state. A proposed alternative must be unique, semantically equivalent, and validated against the intended control. Never auto-edit source, bypass assertions, or accept a locator based on confidence score alone. Changes require review and regression execution.

## Accessibility
Prefer accessible locators because they validate user-facing semantics. A test-ID locator does not replace accessibility testing.
