---
name: qa-test-design
description: Translating business requirements, flight schemas, and NDC workflows into structured test cases.
---

# Skill: QA Test Design

## Purpose
Enables autonomous agents to analyze product specifications, user stories, and OpenAPI contracts to construct exhaustive, deterministic test specifications across positive, negative, boundary, concurrency, and security dimensions.

## Methodologies
1. **Equivalence Partitioning & Boundary Value Analysis (BVA)**:
   - Identify valid and invalid input domains for flight seat counts (1-9 seats allowed; 0 and 10 tested as boundaries).
   - Evaluate monetary cart pricing and ancillary combinations.
2. **State Transition Modeling**:
   - Trace order lifecycle: `INITIATED` -> `CONFIRMED` -> `PAID` -> `CANCELLED` -> `REFUNDED`.
3. **Intentional Defect Alignment**:
   - Reference `DEF-001` through `DEF-005` in test matrices to detect regression vulnerabilities.
