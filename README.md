# QA Intelligence Hub

[![CI Pipeline](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/react-19.2-61dafb.svg)](https://react.dev/)
[![Playwright](https://img.shields.io/badge/playwright-v1.50+-2EAD33.svg)](https://playwright.dev/)
[![Docker Ready](https://img.shields.io/badge/docker-compose-2496ED.svg)](docker/compose.portfolio.yaml)
[![Quality Gate: Strict](https://img.shields.io/badge/quality%20gate-PRODUCTION__STRICT-brightgreen.svg)](qa-engine/quality_gate.py)

A production-grade, AI-powered Quality Engineering platform demonstrating modern software testing architecture across UI, REST API, Database Invariants, AI/RAG Evaluation, Agentic QA, DAST Security, Performance Benchmarking, Defect Engineering, Multi-Signal Release Quality Gates, and CI/CD.

Designed as a production-grade Quality Engineering platform demonstrating Senior SDET & Quality Platform Architecture.

> **Latest verified main baseline (2026-10-10; live production smoke rechecked 2026-10-16)**: [GitHub Actions run #38038639739](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/runs/38038639739) passed for main commit `5779a51686f7a73f1d5d479b74b7bf68d0728d92`. Backend: **447/447 Pytest passed**; Playwright: **82/82 E2E passed**; total **529 executed CI test items**. The backend and E2E `PRODUCTION_STRICT` quality gates were APPROVED; DAST reported **5/5 probes passed, 0 vulnerabilities**. The required `backend`, `frontend`, `e2e`, and `checkpoint` jobs all passed. The matching Vercel production deployment is READY and the live serving-revision endpoint reports the same SHA.
>
> **Live read-only production smoke (2026-10-16)**: `/`, `/health`, `/qa/release/serving-revision`, `/openapi.json`, `/docs`, `/qa/catalog/summary`, `/qa/layers?include_all=true`, `/qa/ai/providers/status`, and `/qa/production/incidents?status=OPEN` returned HTTP 200. The incidents endpoint reported zero open incidents. AI is explicitly `HERMETIC_OFFLINE_MOCK`; no live Gemini/Claude/OpenAI integration is claimed. These smoke checks were read-only.
>
> **Evidence-count and freshness note**: The live capability catalog contains **492 capabilities** across 11 layers. The Test Explorer's stored execution snapshot (`RUN-AUTO-20261007-115444`, **426/426 PASS**) is historical and tied to commit `27848c25e9a88f17e6925b3e63c4d1032b1bc697`; it is not a fresh run of the current production revision. Catalog capabilities, CI test executions, and stored Test Explorer evidence are distinct counters and must not be presented as interchangeable. Use the revision-bound CI run and its artifacts for current test execution evidence.
>
> **Portfolio Architecture**: **Reusable QA Platform Core + Pluggable Multi-Domain Packs**. Five industry domain packs (Airline/NDC, Healthcare/FHIR, FinTech/Banking, E-Commerce/Retail, and Telecom/5G Mobile) operate as distinct, isolated domain plugins under a unified test harness without modifying the platform core. Features dynamic runtime domain selection via `QA_DOMAIN` and an automated end-to-end Portfolio Demonstration CLI (`qa-engine/portfolio_demo.py`). All test data, schemas, and workflows are 100% synthetic public standards; zero proprietary employer data.

---

## 🏗️ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          QA INTELLIGENCE HUB           │
                      └───────────────────┬────────────────────┘
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       ▼                                  ▼                                  ▼
┌──────────────┐                 ┌─────────────────┐                ┌──────────────────┐
│  SUT Engine  │                 │    QA Engine    │                │    AI Engine     │
├──────────────┤                 ├─────────────────┤                ├──────────────────┤
│ - Flights    │                 │ - Test Runner   │                │ - Provider Layer │
│ - Bookings   │                 │ - Regression    │                │ - RAG Pipeline   │
│ - 3DS ACS    │                 │ - Quality Gate  │                │ - 10D Eval Suite │
│ - Defect Sw. │                 │ - Evidence Hub  │                │ - Vector Index   │
└──────┬───────┘                 └────────┬────────┘                └────────┬─────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │   AGENT ORCHESTRATOR    │
                             │ (Specialist QA Agents)  │
                             └────────────┬────────────┘
                                          │
       ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                  ▼                               ▼                  ▼
┌──────────────┐   ┌──────────────┐                ┌──────────────┐   ┌──────────────┐
│ Requirement  │   │  Defect RCA  │                │   Security   │   │  Reporting   │
│    Agent     │   │    Agent     │                │  DAST Agent  │   │ Release Sign │
└──────────────┘   └──────────────┘                └──────────────┘   └──────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    FastMCP Server (JSON-RPC Tools)     │
                      │  7 Standardized Agent Tools & Skills   │
                      └───────────────────┬────────────────────┘
                                          │
       ┌──────────────────────────────────┴──────────────────────────────────┐
       ▼                                                                     ▼
┌──────────────────────────────┐                       ┌──────────────────────────────┐
│  Single Pane React 19 UI     │                       │     GitHub Actions CI/CD     │
│  - SUT Aviation Booking      │                       │  - Revision-Bound CI Checks   │
│  - AI Evaluation & RAG Lab   │                       │  - PostgreSQL Service Cont.  │
│  - DAST Security Auditor     │                       │  - Strict Gate Step Summary  │
│  - Test Runner & Impact Sim  │                       │  - Playwright E2E Headless   │
│  - Capability & Evidence Hub │                       │  - Frontend Lint & TS Build  │
└──────────────────────────────┘                       └──────────────────────────────┘
```

---

## ⚡ Key Platform Capabilities

| Capability | Implementation & Technology | Location |
|---|---|---|
| **Master Agent Orchestrator** | Full closed-loop autonomous execution cycle (Discover -> Plan -> Execute -> Evidence -> Security -> Quality Gate) | [`qa-engine/orchestrator.py`](qa-engine/orchestrator.py) |
| **Master Capability Inventory** | Dynamic catalog manager tracking 492 catalog capabilities across 11 layers & 5 domains | [`qa-engine/catalog_manager.py`](qa-engine/catalog_manager.py) |
| **Structured Evidence Engine** | Machine-readable execution telemetry records with pass rates, assertion traces, and commit SHA | [`qa-engine/evidence_engine.py`](qa-engine/evidence_engine.py) |
| **Multi-Domain Architecture** | Pluggable Domain Packs for Airline (NDC), Healthcare (HL7 FHIR), FinTech (ISO 20022), E-Commerce (Retail), and Telecom (5G Mobile) with `QA_DOMAIN` switching | [`domains/`](domains/) |
| **System Under Test (SUT)** | Realistic Airline NDC booking, seat inventory, 7 payment methods, 3DS challenge | [`backend/app/routers/`](backend/app/routers/) |
| **Defect Injection Engine** | 29 documented defect switches across Airline (5), Healthcare (6), FinTech (6), E-Commerce (6), and Telecom (6) | [`backend/app/core/defects.py`](backend/app/core/defects.py) |
| **Database Validation** | Constraints, foreign key cascades, rollback isolation, atomic inventory deduction | [`tests/database/`](tests/database/) |
| **Regression Selector** | PR git diff impact analyzer mapping changed files to targeted test suites | [`qa-engine/regression_selector.py`](qa-engine/regression_selector.py) |
| **AI / RAG Architecture** | Dual-plane RAG (Ingestion & Query) with provider abstraction (Gemini, Claude, OpenAI, Mock) | [`ai-engine/`](ai-engine/) |
| **10D RAG Evaluation Suite** | 10-dimensional evaluation dataset covering standard, adversarial, hallucination probes, and refusal | [`ai-engine/rag_dataset.py`](ai-engine/rag_dataset.py) |
| **Agentic QA** | 5 Specialist Agents (`Requirement`, `DefectRCA`, `SecurityTesting`, `Reporting`, `UIHealing`) | [`ai-engine/agents.py`](ai-engine/agents.py) |
| **Self-Healing UI** | Automated Playwright locator recovery analyzing failure traces and synthesizing W3C ARIA roles | [`ai-engine/agents.py`](ai-engine/agents.py) |
| **MCP Integration** | FastMCP server exposing 7 standardized tools with schema validation | [`ai-engine/mcp_server.py`](ai-engine/mcp_server.py) |
| **Security Testing (DAST)** | Automated OWASP Top 10, IDOR, SQLi, XSS, PCI DSS PAN masking, Prompt Injection | [`tests/security/`](tests/security/) |
| **High-Concurrency Load** | Async load engine + Locust NDC user journey scenario collecting p50/p90/p95/p99 & RPS | [`qa-engine/load_generator.py`](qa-engine/load_generator.py) |
| **Release Quality Gate** | Multi-signal evaluator with configurable policy tiers & PostgreSQL audit history | [`qa-engine/quality_gate.py`](qa-engine/quality_gate.py) |
| **Portfolio Demo CLI** | Unified 7-module automated demonstration runner validating senior QE architecture across 5 domains | [`qa-engine/portfolio_demo.py`](qa-engine/portfolio_demo.py) |
| **Executive Sign-Off** | AI-generated GO/NO-GO release governance report with risk analysis table | [`backend/app/routers/qa.py`](backend/app/routers/qa.py) |

---

## 🧪 Comprehensive 11-Layer Test Pyramid

The platform organizes validation across 11 architecture layers. The latest verified main CI run (#38038639739, commit `5779a51686f7a73f1d5d479b74b7bf68d0728d92`) executed **447 backend tests + 82 Playwright E2E tests = 529 CI test items**, all passing. The live capability catalog contains **492 capabilities**. The Test Explorer still serves a historical 426-test snapshot from 7 October 2026 and must not be described as the current CI run. These are separate evidence models:

```
tests/
├── unit/             # Multi-domain registry, portfolio runner, data factories, pure validation (68 tests)
├── api/              # SUT endpoints, quality gate REST APIs, QA platform routers (66 tests)
├── ui/               # Playwright TypeScript E2E suite with Page Object Models (60 tests)
├── contract/         # OpenAPI schema compliance & contract testing (5 tests)
├── database/         # PostgreSQL schema invariants, foreign keys, atomic mutations (18 tests)
├── ai/               # LLM provider fallback, 10-dimensional RAG evaluation audit (67 tests)
├── agents/           # Specialist agent benchmarking, tool guardrails, report generation (44 tests)
├── security/         # DAST vulnerabilities, SQL injection, XSS, PCI DSS masking (41 tests)
├── performance/      # Concurrent p95 latency thresholds (<250ms), load test suite (6 tests)
├── domains/          # Multi-domain pack isolation: Airline, Healthcare, FinTech, E-Commerce, Telecom (83 tests)
└── regression/       # PR diff impact analysis, multi-domain patterns, tag registry (12 tests)
```

### Running Tests & Portfolio Demonstration Locally:

```bash
# 1. Run Master Autonomous Orchestrator Closed-Loop (All phases & Quality Gate)
python qa-engine/orchestrator.py

# 2. Run Complete Portfolio Demonstration (7 QE Modules, <300ms)
python qa-engine/portfolio_demo.py

# 3. Run All Backend Pytest Automated Tests
pytest -q

# 4. Run Targeted Domain or Layer Test Suites
pytest tests/domains/airline/ -v
pytest tests/domains/healthcare/ -v
pytest tests/domains/fintech/ -v
pytest tests/domains/ecommerce/ -v
pytest tests/domains/telecom/ -v
pytest tests/ai/test_rag_comprehensive_audit.py -v
pytest tests/security/ -v
pytest tests/database/ -v

# 5. Run Playwright E2E UI Suite (Headless)
npx playwright test
```

---

## 🚀 Quickstart

### Option 1: Docker Compose (Full-Stack 3-Tier)
Spins up PostgreSQL 18, FastAPI Backend, and Nginx-served React Frontend:

```bash
docker compose -f docker/compose.portfolio.yaml up --build -d
```
- **Web Dashboard**: http://localhost:3000
- **API Swagger Docs**: http://localhost:8000/docs
- **Health Endpoint**: http://localhost:8000/health

### Option 2: Local Developer Mode

```bash
# 1. Start Backend (falls back automatically to in-memory SQLite if DATABASE_URL is unset)
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
PYTHONPATH=.:../qa-engine:../ai-engine uvicorn app.main:app --reload --port 8000

# 2. Start Frontend
cd ../frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

---

## 🌐 Production Deployment

The active production topology is a **unified Vercel deployment** serving the React frontend and FastAPI API from the same project, backed by Neon PostgreSQL. The canonical production alias is:

**https://qa-intelligence-hub-flax.vercel.app**

Current production certification evidence (rechecked 2026-10-16):

- **Latest verified code-bearing CI baseline SHA:** `5779a51686f7a73f1d5d479b74b7bf68d0728d92`.
- **GitHub Actions run #38038639739:** PASS — 447 backend tests + 82 Playwright E2E tests; backend/frontend/E2E/checkpoint jobs all passed.
- **Quality gates:** `PRODUCTION_STRICT` APPROVED for backend and E2E; DAST 5/5 probes passed with 0 vulnerabilities.
- **Production deployment:** [Vercel deployment details](https://vercel.com/qa-intelligence-hub/qa-intelligence-hub/2v2J4XBzqPg1XpaQgsjnMFfSzp4y), state READY, Git SHA `5779a51686f7a73f1d5d479b74b7bf68d0728d92`.
- **Live serving revision:** Rechecked via `/qa/release/serving-revision`; returned the same SHA as the production deployment.
- **Stored Test Explorer evidence:** Historical run `RUN-AUTO-20261007-115444`, 426/426 PASS, commit `27848c25e9a88f17e6925b3e63c4d1032b1bc697`. This snapshot remains stale relative to the deployed revision and is not substituted for CI evidence.
- **AI mode:** `HERMETIC_OFFLINE_MOCK`; live Gemini/Claude/OpenAI providers are not configured.
- **Live smoke:** The listed read-only endpoints returned HTTP 200 on 2026-10-16; open production incidents endpoint returned 0 incidents.

These checks confirm the stated SHA and endpoints. They do not imply that every business workflow was rerun against production; mutating E2E tests remain restricted to isolated environments.

Legacy deployment references elsewhere in the repository are historical or alternate deployment configurations; they are not the authoritative current topology.

Complete deployment runbook and environment-variable reference: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## 📖 Engineering Documentation

- [Architecture & Data Flow Diagrams](docs/ARCHITECTURE.md)
- [Production Deployment Runbook](docs/DEPLOYMENT.md)
- [Domain Pack Extension Guide](docs/domain-extension-guide.md)
- [Project Roadmap & Completed Milestones](docs/ROADMAP.md)
- [Engineering Standards & Architectural Rules](AGENTS.md)
