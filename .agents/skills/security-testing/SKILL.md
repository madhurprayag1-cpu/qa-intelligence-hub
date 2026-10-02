---
name: security-testing
description: Security verification covering IDOR protection, JWT token validation, injection defenses, and PCI DSS masking.
---

# Skill: Security Testing

## Purpose
Ensures security is a first-class quality discipline (AGENTS.md Section 21) across all APIs, database calls, and UI components.

## Attack Vectors & Verification
1. **Insecure Direct Object Reference (IDOR)**:
   - Verify Passenger A cannot access or cancel Passenger B's booking by manipulating sequential integer IDs.
2. **Authentication & RBAC**:
   - Verify unauthenticated requests return 401 Unauthorized.
   - Verify non-privileged roles (e.g. `passenger`) cannot invoke administrative actions (Quality Gate override).
3. **Sensitive Data Exposure (PCI DSS)**:
   - Ensure full credit card PANs and CVV security codes are never persisted in databases, printed in application logs, or reflected in API responses.
4. **Injection Resiliency**:
   - Verify raw SQL payloads and XSS `<script>` tags are sanitized and handled via parameterized queries.
