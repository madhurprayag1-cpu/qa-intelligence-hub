\# AGENTS.md



\## 1. Project Identity



Project: QA Intelligence Hub



Purpose:

Build a production-oriented, AI-powered Quality Engineering platform that demonstrates

modern software testing capabilities across UI, API, database, AI/RAG, agentic AI,

security, performance, regression, defect analysis, observability, and CI/CD.



This is a portfolio project designed to demonstrate Senior SDET / Quality Engineering

architecture and implementation skills.



The system must be realistic, scalable, maintainable, testable, and deployable.



\---



\## 2. Core Engineering Principle



Build one connected system, not a collection of unrelated demos.



The major components must integrate through clear contracts:



SUT

→ UI

→ REST APIs

→ Database

→ AI/RAG

→ QA Engine

→ Agentic QA

→ Test Execution

→ Results

→ Defect/RCA

→ Quality Gate

→ Dashboard

→ CI/CD



Prefer simple, modular architecture that can evolve into distributed services later.



Do not introduce unnecessary microservices during the initial implementation.



\---



\## 3. Primary Technology Direction



Frontend:

\- React

\- TypeScript

\- Modern component architecture

\- Accessible UI

\- Responsive design



Backend:

\- Python

\- FastAPI

\- Pydantic

\- REST APIs



Database:

\- PostgreSQL



UI Automation:

\- Playwright

\- TypeScript



API Testing:

\- Python

\- pytest

\- HTTP client tooling

\- Contract/schema validation



AI / RAG:

\- Provider-independent architecture

\- Embeddings

\- Vector search

\- Retrieval evaluation

\- LLM evaluation



AI providers must be replaceable.



Potential providers:

\- Google Gemini

\- Anthropic Claude

\- OpenAI



Never tightly couple business logic to one AI provider.



\---



\## 4. AI Provider Abstraction



Implement an abstraction layer for AI providers.



Application code must communicate through interfaces such as:



AIProvider

EmbeddingProvider

LLMProvider

AgentModelProvider



Provider-specific implementations belong behind the abstraction.



Example:



GeminiProvider

ClaudeProvider

OpenAIProvider



Switching providers must not require rewriting business logic, tests, agents,

or the frontend.



Never hard-code provider-specific behavior throughout the application.



\---



\## 5. QA Intelligence Capabilities



The platform should progressively support:



1\. Requirement analysis

2\. Test case generation

3\. Test data generation

4\. API testing

5\. UI testing

6\. Database validation

7\. Contract testing

8\. Regression testing

9\. Defect detection

10\. Root cause analysis

11\. RAG evaluation

12\. LLM evaluation

13\. Agent evaluation

14\. Security testing

15\. Performance testing

16\. Quality gates

17\. Release readiness analysis

18\. Test reporting

19\. Observability



Each capability must integrate with the central QA platform.



\---



\## 6. Agentic QA Architecture



Use specialist agents where they provide clear value.



Potential agents:



\- Requirement Agent

\- Test Generation Agent

\- API Testing Agent

\- UI Testing Agent

\- Regression Agent

\- Defect RCA Agent

\- RAG Evaluation Agent

\- LLM Evaluation Agent

\- Agent Evaluation Agent

\- Security Testing Agent

\- Performance Testing Agent

\- Database Validation Agent

\- Release Quality Agent

\- Reporting Agent



Agents must use explicit tools and contracts.



Agents must not directly manipulate arbitrary application state.



Agent actions should be:

\- observable

\- auditable

\- reproducible where possible

\- permission controlled

\- traceable to a test/run/request ID



\---



\## 7. MCP and Agent Skills



Use MCP for tool integration where appropriate.



Keep MCP configuration independent from model providers.



Use reusable Agent Skills for specialized QA workflows.



Potential skills:



\- qa-test-design

\- api-testing

\- playwright-testing

\- database-testing

\- llm-evaluation

\- rag-evaluation

\- agent-testing

\- root-cause-analysis

\- security-testing

\- performance-testing

\- release-quality-gate



Skills must be portable and should not depend on one AI vendor.



\---



\## 8. System Under Test



The project must contain its own synthetic but realistic application.



Do not depend on unstable public websites or APIs for core functionality.



The SUT should eventually include realistic workflows such as:



\- authentication

\- search

\- product/flight search

\- details

\- booking/order creation

\- payment

\- ancillary services

\- cancellation

\- refunds

\- order retrieval

\- administrative workflows



The domain may use airline/ticketing/NDC concepts as a differentiator.



All data must be synthetic.



Never copy confidential employer data.



Never include proprietary company data, credentials, tokens, customer information,

production traces, or internal documentation.



\---



\## 9. Defect Engineering



The SUT should contain intentionally introduced defects for QA demonstration.



Examples:



\- incorrect validation

\- incorrect calculations

\- stale data

\- UI/API mismatch

\- authorization defects

\- workflow defects

\- race conditions

\- incorrect error handling

\- missing edge cases

\- contract mismatches

\- database consistency problems

\- AI hallucinations

\- RAG retrieval failures

\- prompt injection vulnerabilities

\- agent tool misuse



Defects must be documented and reproducible.



Do not hide defects inside random code.



\---



\## 10. RAG Architecture



RAG must be designed for scale.



Do NOT hard-code assumptions such as:



"5 PDFs"



or



"10 documents"



The architecture must support increasing document volume without rewriting

the core system.



Use separate concepts for:



Ingestion Plane:

document upload

→ parsing

→ extraction

→ chunking

→ metadata

→ embeddings

→ indexing



Query Plane:

query

→ retrieval

→ optional reranking

→ context construction

→ model

→ answer

→ evaluation



Store metadata such as:



\- document ID

\- version

\- source

\- chunk ID

\- page

\- timestamps

\- embedding model

\- ingestion status



\---



\## 11. Test Architecture



Tests must be organized by purpose.



Recommended layers:



tests/

&#x20; unit/

&#x20; api/

&#x20; ui/

&#x20; integration/

&#x20; contract/

&#x20; database/

&#x20; ai/

&#x20; rag/

&#x20; agents/

&#x20; security/

&#x20; performance/

&#x20; regression/



Prefer a test pyramid.



Unit tests should be fast.



Integration tests should validate component contracts.



UI tests should focus on important business journeys.



End-to-end tests should be limited to high-value workflows.



\---



\## 12. Test Data



Test data must be:



\- synthetic

\- deterministic where appropriate

\- configurable

\- reusable

\- environment independent

\- generated through factories/builders where practical



Do not scatter hard-coded test data throughout tests.



Use configuration and fixtures.



Support positive, negative, boundary, security, concurrency, and failure scenarios.



\---



\## 13. API Engineering



Every API must have:



\- clear request/response models

\- validation

\- meaningful HTTP status codes

\- structured errors

\- logging

\- correlation/request IDs

\- authentication where required

\- authorization where required

\- OpenAPI documentation



Do not expose internal exceptions directly to API consumers.



\---



\## 14. Database Engineering



Use PostgreSQL for persistent application data.



Database changes must be migration based.



Avoid destructive schema changes without explicit migration handling.



Use:



\- constraints

\- indexes

\- foreign keys

\- transactions

\- appropriate normalization

\- audit fields where useful



Database tests must verify both data correctness and business rules.



\---



\## 15. UI Engineering



Frontend code must prioritize:



\- accessibility

\- semantic HTML

\- reusable components

\- clear state management

\- loading states

\- error states

\- empty states

\- responsive behavior

\- predictable selectors for automation



Avoid brittle selectors.



Prefer stable test IDs or semantic selectors where appropriate.



\---



\## 16. Playwright Standards



Use Playwright with TypeScript.



Tests must use:



\- page objects or appropriate abstractions

\- fixtures

\- reusable utilities

\- deterministic test data

\- trace/video/screenshot collection where useful



Avoid:



\- arbitrary long sleeps

\- fragile XPath

\- duplicated login logic

\- hard-coded environment URLs

\- tests dependent on execution order



Prefer explicit waits based on application state.



\---



\## 17. API Test Standards



API tests must validate:



\- status codes

\- schema

\- headers

\- response body

\- business rules

\- negative scenarios

\- authorization

\- data persistence where appropriate



Tests should be independent whenever possible.



\---



\## 18. AI / LLM Testing



AI functionality must not be tested only by checking exact strings.



Use appropriate evaluation dimensions:



\- correctness

\- relevance

\- groundedness

\- faithfulness

\- completeness

\- consistency

\- safety

\- latency

\- token/cost metrics

\- refusal behavior

\- hallucination rate



Use deterministic checks where possible and rubric/model-based evaluation where necessary.



AI evaluation datasets must be version controlled.



\---



\## 19. RAG Evaluation



RAG tests should evaluate both retrieval and generation.



Retrieval metrics may include:



\- recall

\- precision

\- hit rate

\- ranking quality

\- context relevance



Generation evaluation may include:



\- groundedness

\- factual consistency

\- answer relevance

\- citation correctness

\- unsupported claim detection



Do not treat a successful HTTP response as a successful RAG result.



\---



\## 20. Agent Testing



Agents must be evaluated on:



\- task completion

\- tool selection

\- tool arguments

\- reasoning outcome

\- safety

\- authorization

\- failure recovery

\- hallucination

\- unnecessary tool calls

\- latency

\- cost

\- reproducibility



Agent tests must verify that agents cannot perform unauthorized operations.



\---



\## 21. Security



Security is a first-class QA concern.



Never commit:



\- API keys

\- passwords

\- tokens

\- certificates

\- private keys

\- secrets

\- production credentials



Use environment variables and secret management.



Security testing should progressively cover:



\- authentication

\- authorization

\- IDOR

\- injection

\- XSS

\- CSRF where applicable

\- SSRF

\- insecure direct object access

\- sensitive data exposure

\- rate limiting

\- prompt injection

\- malicious document ingestion

\- agent tool abuse



\---



\## 22. Observability



Every important workflow should be traceable.



Capture appropriate metadata such as:



\- request ID

\- test ID

\- run ID

\- agent ID

\- model/provider

\- tool calls

\- timestamps

\- latency

\- token usage

\- result

\- error

\- environment



Do not log secrets or sensitive data.



\---



\## 23. CI/CD



GitHub Actions will be used for CI/CD.



The pipeline should progressively include:



1\. formatting

2\. linting

3\. unit tests

4\. API tests

5\. integration tests

6\. UI tests

7\. security checks

8\. AI evaluation

9\. build

10\. deployment

11\. quality gate



A pull request must not be considered successful merely because the application builds.



Quality checks must be meaningful.



\---



\## 24. Quality Gate



The platform should eventually provide a release quality gate based on configurable criteria.



Potential signals:



\- test pass rate

\- critical defect count

\- regression failures

\- security findings

\- API contract failures

\- AI evaluation score

\- RAG evaluation score

\- performance thresholds

\- flaky test rate



Do not hard-code one universal threshold.



Quality policies must be configurable.



\---



\## 25. Scalability



Design for scale from the beginning.



Avoid unnecessary complexity in the MVP, but do not create architectural dead ends.



The system should eventually support:



\- larger document collections

\- larger test suites

\- parallel test execution

\- multiple environments

\- multiple AI providers

\- multiple agents

\- background jobs

\- queue-based execution

\- persistent run history

\- horizontal scaling



Prefer configuration-driven behavior.



\---



\## 26. Error Handling



Errors must be:



\- explicit

\- structured

\- actionable

\- logged appropriately

\- safe for external consumers



Never silently swallow exceptions.



Never use broad exception handling unless there is a documented reason.



\---



\## 27. Code Quality



Follow clean-code principles.



Prefer:



\- small focused functions

\- meaningful names

\- strong typing

\- clear interfaces

\- dependency injection where useful

\- separation of concerns

\- reusable components

\- testable modules



Avoid:



\- giant files

\- giant functions

\- duplicated logic

\- hidden global state

\- magic numbers

\- unnecessary abstractions

\- premature optimization



\---



\## 28. AI Coding Rules



AI agents are encouraged to accelerate development.



However:



AI-generated code must be reviewed.



AI-generated code must be tested.



AI agents must not invent requirements.



AI agents must not silently change architecture.



AI agents must explain significant architectural decisions when requested.



Prefer incremental changes over massive rewrites.



Before modifying existing behavior, inspect the relevant code and tests.



\---



\## 29. Change Discipline



For every meaningful change:



1\. Understand the existing implementation.

2\. Identify affected components.

3\. Make the smallest reasonable change.

4\. Add or update tests.

5\. Run relevant validation.

6\. Review the diff.

7\. Update documentation when behavior changes.



Do not modify unrelated files.



\---



\## 30. Git Workflow



Main branch:



main



Use feature branches for meaningful changes.



Recommended pattern:



feature/<short-description>

fix/<short-description>

test/<short-description>

docs/<short-description>



Commit messages should be meaningful.



Prefer small logical commits.



Do not commit generated secrets, local environment files, IDE state,

build artifacts, or dependency caches.



\---



\## 31. Documentation



Important architecture and behavior must be documented.



The repository should progressively contain:



\- README.md

\- architecture documentation

\- setup instructions

\- API documentation

\- testing strategy

\- AI/RAG evaluation strategy

\- agent architecture

\- security documentation

\- contribution guide

\- release process

\- troubleshooting guide



Documentation must reflect the actual implementation.



Do not document features that do not exist.



\---



\## 32. Environment Management



Support separate configuration for:



\- local

\- test

\- CI

\- production



Never hard-code environment-specific URLs, credentials, ports, or API keys.



Use environment variables/configuration.



Provide safe example configuration files where needed.



\---



\## 33. Docker



Docker should be used to make local setup reproducible.



Containers may eventually include:



\- frontend

\- backend

\- PostgreSQL

\- supporting services



Keep container configuration understandable.



Do not add infrastructure merely for appearance.



\---



\## 34. Deployment



The project should eventually support public demonstration.



Target direction:



GitHub

→ CI/CD

→ deployment

→ live application



Vercel may be used for suitable frontend/application workloads.



Backend/database infrastructure must use an appropriate deployment target.



Never expose development credentials publicly.



\---



\## 35. Portfolio Quality



This project must demonstrate Senior-level engineering.



Prioritize:



\- architecture

\- reliability

\- automation

\- maintainability

\- observability

\- security

\- AI quality

\- realistic testing

\- CI/CD

\- measurable quality outcomes



Avoid building features only because they look impressive.



Every major feature should solve a recognizable QA/engineering problem.



\---



\## 36. Interview Defensibility



The developer must be able to explain:



\- why the architecture was chosen

\- why technologies were selected

\- how tests are structured

\- how AI is evaluated

\- how RAG is evaluated

\- how agents are tested

\- how defects are detected

\- how RCA works

\- how CI/CD works

\- how scalability is addressed

\- how security is tested

\- how AI provider switching works

\- what trade-offs were made



Do not create opaque AI-generated implementations that cannot be explained.



\---



\## 37. Definition of Done



A feature is NOT complete when code has merely been generated.



A feature is complete only when appropriate:



\- implementation exists

\- tests exist

\- validation passes

\- error handling exists

\- documentation is updated where necessary

\- security considerations are addressed

\- observability is considered

\- Git diff is reviewed



For user-facing features, the relevant UI/API/integration workflow must also be verified.



\---



\## 38. Agent Behavior



Before making significant changes:



\- inspect the repository

\- understand the existing architecture

\- identify relevant instructions

\- avoid unnecessary changes



When uncertain:



\- prefer existing project conventions

\- ask for clarification rather than inventing business requirements

\- preserve backward compatibility unless a breaking change is intentional



Never remove working functionality without explicit justification.



\---



\## 39. Long-Term Architecture Goal



The final platform should resemble a small production-grade Quality Engineering

platform rather than a tutorial application.



Target conceptual architecture:



&#x20;               QA INTELLIGENCE HUB

&#x20;                       |

&#x20;       +---------------+---------------+

&#x20;       |               |               |

&#x20;      SUT           QA ENGINE       AI ENGINE

&#x20;       |               |               |

&#x20;  UI/API/DB      Test Execution     RAG/LLM

&#x20;       |               |               |

&#x20;       +---------------+---------------+

&#x20;                       |

&#x20;                 AGENT ORCHESTRATOR

&#x20;                       |

&#x20;       +---------------+---------------+

&#x20;       |               |               |

&#x20;     Agents          Tools          Skills

&#x20;                       |

&#x20;                 RESULTS / EVENTS

&#x20;                       |

&#x20;            +----------+----------+

&#x20;            |                     |

&#x20;         RCA / DEFECT        QUALITY GATE

&#x20;            |                     |

&#x20;            +----------+----------+

&#x20;                       |

&#x20;                   DASHBOARD

&#x20;                       |

&#x20;                   CI/CD



The architecture may evolve, but all major components must remain connected

through explicit contracts and observable workflows.



\---



\## 40. Final Principle



Build for real engineering value.



The goal is not to demonstrate that AI can generate code.



The goal is to demonstrate that a Senior Quality Engineer can use AI,

automation, software engineering, testing strategy, and intelligent agents

to build a reliable quality platform.

## Context7 Usage Policy

- Use Context7 when implementing, debugging, or reviewing code that depends on current or version-specific third-party APIs or documentation. Prefer official docs for project dependencies such as Playwright, FastAPI, SQLAlchemy, Pydantic, pytest, Vercel, Neon, and GitHub Actions.
- For repository-local knowledge, inspect `AGENTS.md`, project skills, source, tests, and docs first; do not call Context7 for general programming knowledge already covered there.
- Run the smallest relevant targeted tests first. Run the full quality gate at meaningful checkpoints, such as feature completion, security-sensitive changes, or before commit/release.
- Never expose or commit API keys, credentials, tokens, or secrets retrieved or used by MCP tools.

