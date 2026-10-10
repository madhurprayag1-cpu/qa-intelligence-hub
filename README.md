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

> **Latest revision-bound CI verification (2026-10-09)**: GitHub Actions run [#88](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/runs/37943142267) completed successfully for main commit `d4b53ef3cacbeb756703b6da8a5ada44a822eba0`. The required `backend`, `frontend`, `e2e`, and `checkpoint` jobs all passed. The matching Vercel production deployment is READY for the same commit. This confirms CI and deployment metadata; it does **not** substitute for a fresh live serving-revision/API smoke check.
>
> **Evidence-count note**: CI test totals, the capability catalog, and stored Test Explorer snapshots are separate evidence sources and can differ by revision. Do not compare or present their counts as interchangeable; use the revision-bound CI artifacts and live API evidence for current certification.
>
> **Portfolio Architecture****: **Reusable QA Platform Core + Pluggable Multi-Domain Packs**. Five industry domain packs (Airline/NDC, Healthcare/FHIR, FinTech/Banking, E-Commerce/Retail, and Telecom/5G Mobile) operate as distinct, isolated domain plugins under a unified test harness without modifying the platform core. Features dynamic runtime domain selection via `QA_DOMAIN` and an automated end-to-end Portfolio Demonstration CLI (`qa-engine/portfolio_demo.py`). All test data, schemas, and workflows are 100% synthetic public standards; zero proprietary employer data.

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
│  - SUT Aviation Booking      │                       │  - 522 Current CI Test Items │
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
| **Master Capability Inventory** | Dynamic catalog manager tracking 475 capabilities across 11 layers & 5 domains | [`qa-engine/catalog_manager.py`](qa-engine/catalog_manager.py) |
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

The platform organizes validation across 11 architecture layers. Current revision-bound CI evidence is **442 backend tests + 80 Playwright E2E tests = 522 test items**. The capability/evidence explorer exposes **492 capabilities**, while the production Test Explorer endpoint currently serves a stored **426-test execution snapshot** at 100% pass. These are distinct evidence models and must not be treated as the same counter:

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

Current production certification evidence:

- **Latest main commit:** `d4b53ef3cacbeb756703b6da8a5ada44a822eba0` (PR #18 payment-form changes).
- **Latest CI evidence:** [GitHub Actions run #88](https://github.com/madhurprayag1-cpu/qa-intelligence-hub/actions/runs/37943142267) — backend, frontend, E2E, and checkpoint jobs all completed successfully for that commit.
- **Vercel production deployment:** [Deployment details](https://vercel.com/qa-intelligence-hub/qa-intelligence-hub/2HPBjoQvuHeXReMCysVzUuHUYeoB), state READY, Git SHA `d4b53ef3cacbeb756703b6da8a5ada44a822eba0`.
- **Live serving revision:** Must be verified at `/qa/release/serving-revision` before making a fresh production certification claim; this README update does not assert a live endpoint check.
- **AI mode:** `HERMETIC_OFFLINE_MOCK` (no live Gemini/Claude/OpenAI provider configured)

Exact serving/deployment identifiers are intentionally kept as externally verified release evidence rather than self-referential README claims, because a documentation-only commit itself creates a new Vercel deployment revision.

Read-only production smoke verification covered the health endpoint, serving-revision endpoint, Test Explorer, run explorer, incident listing, flights, flight search, airports, QA layers, Swagger docs, OpenAPI, runtime metrics, and AI-provider status.

Legacy deployment references elsewhere in the repository are historical or alternate deployment configurations; they are not the authoritative current topology.

Complete deployment runbook and environment-variable reference: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## 📖 Engineering Documentation

- [Architecture & Data Flow Diagrams](docs/ARCHITECTURE.md)
- [Production Deployment Runbook](docs/DEPLOYMENT.md)
- [Domain Pack Extension Guide](docs/domain-extension-guide.md)
- [Project Roadmap & Completed Milestones](docs/ROADMAP.md)
- [Engineering Standards & Architectural Rules](AGENTS.md)
