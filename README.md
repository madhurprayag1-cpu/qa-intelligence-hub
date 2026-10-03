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

> **Current verified release state (October 3, 2026)**: The latest GitHub Actions CI run **#34** passed successfully for commit **`5307d78084549c8f06b004afd90a4b61e632ece8`**. The validated pipeline includes backend, frontend, Playwright E2E, and checkpoint jobs. The production Vercel deployment is **READY** and is serving this exact commit. See [docs/ROADMAP.md](docs/ROADMAP.md) for the canonical project state.

## Current Project Status

| Area | Current verified state |
|---|---|
| **Architecture** | Five isolated production domain packs: Airline/NDC, Healthcare/FHIR, FinTech/Banking, E-Commerce/Retail, Telecom/5G |
| **Automated validation** | **367 backend Pytest tests + 60 Playwright E2E tests**; latest release CI passed |
| **CI/CD** | GitHub Actions run **#34** — backend, frontend, E2E, and checkpoint jobs all passed |
| **Release revision** | `5307d78084549c8f06b004afd90a4b61e632ece8` |
| **Production** | Vercel deployment **READY**, serving the exact release revision |
| **Production smoke verification** | Read-only checks passed for `/health`, `/flights`, valid `/search/flights`, `/docs`, `/openapi.json`, and the frontend root |
| **Current stage** | Release hardening, repository governance, and portfolio documentation synchronization |

This repository is now in **finalization rather than feature-expansion mode**. The implementation scope covers the five-domain QA platform, AI/RAG and agentic capabilities, security/performance testing, quality gates, CI/CD, and public deployment. Remaining work is focused on keeping documentation and repository governance synchronized with the verified implementation.

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
│ - 3DS ACS    │                 │ - Quality Gate  │                │ - Eval Metrics   │
│ - Defect Sw. │                 │ - Audit Logging │                │ - Vector Index   │
└──────┬───────┘                 └────────┬────────┘                └────────┬─────────┘
       │                                  │                                  │
       └──────────────────────────────────┼──────────────────────────────────┘
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
│  - SUT Aviation Booking      │                       │  - 427 Automated Tests       │
│  - AI Evaluation & RAG Lab   │                       │  - PostgreSQL Service Cont.  │
│  - DAST Security Auditor     │                       │  - Strict Gate Step Summary  │
│  - Test Runner & Impact Sim  │                       │  - Playwright E2E Headless   │
│  - Self-Healing UI & Stress  │                       │  - Frontend Lint & TS Build  │
└──────────────────────────────┘                       └──────────────────────────────┘
```

---

## ⚡ Key Platform Capabilities

| Capability | Implementation & Technology | Location |
|---|---|---|
| **Multi-Domain Architecture** | Pluggable Domain Packs for Airline (NDC), Healthcare (HL7 FHIR), FinTech (ISO 20022), E-Commerce (Retail), and Telecom (5G Mobile) with `QA_DOMAIN` switching | [`domains/`](domains/) |
| **System Under Test (SUT)** | Realistic Airline NDC booking, seat inventory, 7 payment methods, 3DS challenge | [`backend/app/routers/`](backend/app/routers/) |
| **Defect Injection Engine** | 29 documented defect switches across Airline (5), Healthcare (6), FinTech (6), E-Commerce (6), and Telecom (6) | [`backend/app/core/defects.py`](backend/app/core/defects.py) |
| **Database Validation** | Constraints, foreign key cascades, rollback isolation, atomic inventory deduction | [`tests/database/`](tests/database/) |
| **Regression Selector** | PR git diff impact analyzer mapping changed files to targeted test suites | [`qa-engine/regression_selector.py`](qa-engine/regression_selector.py) |
| **AI / RAG Architecture** | Dual-plane RAG (Ingestion & Query) with provider abstraction (Gemini, Claude, OpenAI, Mock) | [`ai-engine/`](ai-engine/) |
| **AI Evaluation Metrics** | Groundedness score, hallucination rate, citation accuracy, answer relevance | [`ai-engine/rag_evaluator.py`](ai-engine/rag_evaluator.py) |
| **Agentic QA** | 5 Specialist Agents (`Requirement`, `DefectRCA`, `SecurityTesting`, `Reporting`, `UIHealing`) | [`ai-engine/agents.py`](ai-engine/agents.py) |
| **Self-Healing UI** | Automated Playwright locator recovery analyzing failure traces and synthesizing W3C ARIA roles | [`ai-engine/agents.py`](ai-engine/agents.py) |
| **MCP Integration** | FastMCP server exposing 7 standardized tools with schema validation | [`ai-engine/mcp_server.py`](ai-engine/mcp_server.py) |
| **Security Testing (DAST)** | Automated OWASP Top 10, IDOR, SQLi, XSS, PCI DSS PAN masking, Prompt Injection | [`tests/security/`](tests/security/) |
| **High-Concurrency Load** | Async load engine + Locust NDC user journey scenario collecting p50/p90/p95/p99 & RPS | [`qa-engine/load_generator.py`](qa-engine/load_generator.py) |
| **Release Quality Gate** | Multi-signal evaluator with configurable policy tiers & PostgreSQL audit history | [`qa-engine/quality_gate.py`](qa-engine/quality_gate.py) |
| **Portfolio Demo CLI** | Unified 7-module automated demonstration runner validating senior QE architecture across 5 domains | [`qa-engine/portfolio_demo.py`](qa-engine/portfolio_demo.py) |
| **Executive Sign-Off** | AI-generated GO/NO-GO release governance report with risk analysis table | [`backend/app/routers/qa.py`](backend/app/routers/qa.py) |

---

## 🧪 Comprehensive 11-Layer Test Pyramid (427 Tests)

The repository organizes automated tests into 11 dedicated layers passing 100% (367 Pytest + 60 Playwright E2E):

```
tests/
├── unit/             # Multi-domain registry, portfolio runner, data factories, pure validation
├── api/              # SUT endpoints, quality gate REST APIs, QA platform routers
├── ui/               # Playwright TypeScript E2E suite with Page Object Models (BasePage core)
├── integration/      # End-to-end multi-component workflows (Booking -> Payment -> Gate)
├── contract/         # OpenAPI schema compliance & contract testing
├── database/         # PostgreSQL schema invariants, foreign keys, atomic mutations
├── ai/               # LLM provider fallback, structured outputs, prompt safety
├── rag/              # Retrieval precision, groundedness, domain-aware retrieval, hallucination detection
├── agents/           # Specialist agent benchmarking, tool guardrails, report generation
├── security/         # DAST vulnerabilities, SQL injection, XSS, PCI DSS masking
├── performance/      # Concurrent p95 latency thresholds (<250ms)
├── domains/          # Multi-domain pack isolation (Airline, Healthcare, FinTech, E-Commerce, Telecom)
└── regression/       # PR diff impact analysis, multi-domain patterns, tag registry
```

### Running Tests & Portfolio Demonstration Locally:

```bash
# 1. Run Complete Portfolio Demonstration (7 QE Modules, <300ms)
python qa-engine/portfolio_demo.py

# Or inspect JSON report format:
python qa-engine/portfolio_demo.py --json

# 2. Run All 367 Backend Pytest Automated Tests
pytest -q

# 3. Run Targeted Domain or Layer Test Suites
pytest tests/domains/airline/ -v
pytest tests/domains/healthcare/ -v
pytest tests/domains/fintech/ -v
pytest tests/domains/ecommerce/ -v
pytest tests/domains/telecom/ -v
pytest tests/security/ -v
pytest tests/database/ -v

# 4. Run Playwright E2E UI Suite (Headless)
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

### Current verified production state

- **Platform:** Vercel
- **Production alias:** [qa-intelligence-hub-flax.vercel.app](https://qa-intelligence-hub-flax.vercel.app)
- **Deployment state:** **READY**
- **Serving revision:** `5307d78084549c8f06b004afd90a4b61e632ece8`
- **GitHub CI:** Run **#34**, completed successfully
- **Verification mode:** Read-only production smoke verification; no production database mutations were performed

Verified production endpoints include:

- `/health` → HTTP 200, healthy API response
- `/flights` → HTTP 200
- `/search/flights` → valid query returned HTTP 200
- `/docs` → HTTP 200
- `/openapi.json` → HTTP 200
- `/` → HTTP 200 frontend response

The available Vercel runtime-error view reported **no runtime errors in the selected verification window**. Browser-console verification is not represented as an independent claim here.

### Deployment architecture

The platform is architected for zero-cost / low-overhead public cloud deployment:

| Tier | Target | Configuration | Details |
|---|---|---|---|
| **Frontend** | Vercel | [`frontend/vercel.json`](frontend/vercel.json) | Built with Vite in `<200ms`, global CDN edge |
| **Backend** | Render / Fly.io | [`render.yaml`](render.yaml) | FastAPI ASGI web service with Blueprint IaC |
| **Database** | Neon / Supabase | PostgreSQL 18 | Managed PostgreSQL with connection pooling |

Complete deployment runbook, environment variable reference, and smoke test commands: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## 📖 Engineering Documentation

- [Architecture & Data Flow Diagrams](docs/ARCHITECTURE.md)
- [Production Deployment Runbook](docs/DEPLOYMENT.md)
- [Domain Pack Extension Guide](docs/domain-extension-guide.md)
- [Project Roadmap & Completed Milestones](docs/ROADMAP.md)
- [Engineering Standards & Architectural Rules](AGENTS.md)
