# Production Deployment Runbook

This guide documents the deployment architectures, configuration requirements, and operational procedures for the **QA Intelligence Hub** across local Docker environments and public cloud targets in accordance with [AGENTS.md Section 32, 33, and 34](../AGENTS.md).

---

## 1. Architecture & Deployment Topologies

```
┌────────────────────────────────────────────────────────┐
│                   Target: Public Cloud                 │
├───────────────────────────┬────────────────────────────┤
│  Frontend (Vercel)        │  Backend API (Render /     │
│  - React 19 + Vite        │  Railway / Fly.io / AWS)   │
│  - SPA rewrite rules      │  - FastAPI ASGI app        │
│  - Static CDN Edge        │  - QA Engine + AI Engine   │
└─────────────┬─────────────┴──────────────┬─────────────┘
              │ HTTPS                      │ psycopg3
              ▼                            ▼
┌───────────────────────────┐ ┌──────────────────────────┐
│ End-User Browser / SDET   │ │ Managed PostgreSQL 18    │
│ Single Pane Dashboard     │ │ (Neon / Supabase / RDS)  │
└───────────────────────────┘ └──────────────────────────┘
```

The system is decoupled into three tiers:
1. **Frontend**: Static single-page application built with Vite + TypeScript + React. Hosted on Vercel with global CDN caching.
2. **Backend**: Containerized ASGI service running FastAPI, SQLAlchemy 2.0 ORM, and specialist AI agents.
3. **Database**: PostgreSQL 18 instance storing flights, seat inventories, bookings, audit records, defect injection toggles, RAG document vectors, and quality gate histories.

---

## 2. Option A: Full-Stack Local Docker Compose

For local evaluation, reproducible demos, and offline testing without cloud credentials:

```bash
# 1. Clone repository
git clone https://github.com/madhurprayag1-cpu/qa-intelligence-hub.git
cd qa-intelligence-hub

# 2. Launch PostgreSQL, Backend API, and Nginx-served Frontend
docker compose -f docker/compose.portfolio.yaml up --build -d

# 3. Verify running containers
docker compose -f docker/compose.portfolio.yaml ps
```

### Exposed Endpoints:
- **Frontend Dashboard**: `http://localhost:3000`
- **Backend OpenAPI Docs**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (configure disposable local `POSTGRES_USER` and `POSTGRES_PASSWORD` environment variables before starting Compose)
- **Health Check**: `http://localhost:8000/health`

---

## 3. Option B: Cloud Production Deployment (Unified Vercel + Neon $0 Free Tier)

### Tier 1: Database (Neon Serverless PostgreSQL Free Tier — $0 / No Credit Card)
1. Sign up at [neon.tech](https://neon.tech) with your GitHub account.
2. Create project `qa-intelligence-hub`.
3. Copy your pooled connection string:
   ```text
   postgresql://<user>:<password>@<endpoint>-pooler.<region>.aws.neon.tech/neondb?sslmode=require
   ```
4. Run one-time local database seed from PowerShell:
   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://<your-neon-pooler-connection-string>"
   cd backend
   python -m app.db.init_db
   Remove-Item Env:\DATABASE_URL
   ```

> [!NOTE]
> **Multi-Domain Database Schema & Migrations**: Multi-domain SUT persistence tables (E-Commerce catalog, orders, returns; FinTech accounts, transactions, KYC; Healthcare patients, practitioners, observations, appointments; Telecom plans, subscribers, SIM swaps, CDRs) are managed via Alembic migration `d4e5f6a7b8c9_add_multidomain_sut_tables.py` (building upon previous revisions through `c2b674d52e19`). Run `alembic upgrade head` to apply all migrations. Domain-scoped vector chunks utilize the `rag_document_chunks.metadata_json` column.

### Tier 2 & 3: Unified Full-Stack Deployment on Vercel Hobby ($0 / No Credit Card)
Deploy both the Vite React SPA frontend and the FastAPI Python serverless backend under a single project using the root [`vercel.json`](../vercel.json):
1. Import repository `madhurprayag1-cpu/qa-intelligence-hub` on [vercel.com](https://vercel.com).
2. Keep **Root Directory** as repository root `./`.
3. Add Environment Variables in Vercel project settings:
   - `DATABASE_URL` = `<your-neon-pooled-connection-string>`
   - `AI_PROVIDER` = `gemini` (or `mock`)
   - `GEMINI_API_KEY` = `<your-gemini-key>` *(optional)*
   - `VITE_API_BASE_URL` = optional; in production the frontend resolves to the same-origin Vercel host when this variable is absent
4. Click **Deploy**. Vercel compiles both the frontend into `frontend/dist` and the Python serverless function at `api/index.py`.

---

## 4. Environment Variables Reference

| Variable | Required | Default / Example | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Optional (falls back to in-memory SQLite) | `postgresql+psycopg://user:pass@host:5432/db` | Database connection string |
| `AI_PROVIDER` | No | `gemini` (or `claude`, `openai`, `mock`) | Active AI engine provider |
| `GEMINI_API_KEY` | If provider is `gemini` | `AIzaSy...` | Google Gemini API key |
| `ANTHROPIC_API_KEY` | If provider is `claude` | `sk-ant-...` | Anthropic Claude API key |
| `OPENAI_API_KEY` | If provider is `openai` | `sk-...` | OpenAI API key |
| `VITE_API_BASE_URL` | No (Frontend only) | Local fallback only | Optional API base; production uses same-origin when absent |
| `QA_DOMAIN` | No | `airline` (or `healthcare`, `fintech`, `ecommerce`, `telecom`) | Active domain pack (default: `airline`) |
| `PORT` | Auto (Render/Cloud) | `8000` | HTTP listening port for Uvicorn |

> [!CAUTION]
> **Security Reminder ([AGENTS.md Section 21](../AGENTS.md#L457-L491))**:
> Never commit `.env` files or API secrets into git. All secrets must be injected through Vercel/Render project settings or CI/CD GitHub Action Secrets.

---

## 5. Post-Deployment Smoke Verification

After deployment, run the automated verification sequence against the public URL:

```bash
# 1. Healthcheck
curl -s https://<backend-url>/health | jq .

# 2. SUT Flight Inventory Verification
curl -s https://<backend-url>/airports | jq .

# 3. Quality Gate Evaluation
curl -s -X POST https://<backend-url>/quality-gate/evaluate \
  -H "Content-Type: application/json" \
  -d '{"test_pass_rate": 0.98, "critical_defects": 0, "security_findings": 0, "rag_score": 0.92}' | jq .

# 4. End-to-End UI Verification (Playwright)
BASE_URL=https://<frontend-url> npx playwright test tests/ui/qa_platform_e2e.spec.ts
```

---

## 6. Platform Demonstration & Walkthrough Guide (5-Minute Tour)

When demonstrating or validating the platform end-to-end, follow this structured walkthrough narrative:

### Step 1: System Under Test (SUT) — Realistic Domain & Data Architecture
- Open the **Flight Search & Booking** view.
- Select route preset `ATH → SKG` (Athens to Thessaloniki).
- Highlight real-time seat inventory calculation (€89.00 / 142 seats available).
- Enter passenger details (`John Doe`, `john.doe@example.com`).
- Select **3D Secure Credit Card** and click **Reserve Flight**.
- Complete the simulated **Access Control Server (ACS) challenge** to demonstrate SCA (Strong Customer Authentication) compliance.
- Copy the generated booking reference (e.g. `QAH-ATHSKG-...`).

### Step 2: Booking Management & Payment Audit Lookup
- Navigate to **Manage & Track Bookings**.
- Paste the booking reference.
- Demonstrate full booking retrieval: passenger name, flight number, confirmed status, and payment transaction metadata.

### Step 3: Intentional Defect Engineering (29 Defect Switches across 5 Domains)
- Switch to the **QA Intelligence Hub** platform view -> **Defect Engineering** sub-tab.
- Explain how the platform documents 29 engineered defects across Airline (5), Healthcare (6), FinTech (6), E-Commerce (6), and Telecom (6):
  - Airline: Overbooking race, fare calculation drift, stale inventory, gateway timeout, schema violation.
  - Healthcare: MRN collision, HIPAA unmasked PII, dosage calculation overflow, stale vitals, FHIR schema violation, clinical hallucination.
  - FinTech: Overdraft balance race, currency precision loss, OFAC sanctions filter bypass, idempotency duplicate debit, ISO 20022 contract mismatch, unmasked account number leakage.
  - E-Commerce: Overselling race, promo stacking exploit, price tampering, order state desync, stale cart hold, refund double credit.
  - Telecom: SIM swap race, CDR overage miscalculation, unauthorized roaming leak, double billing CDR race, invalid state transition, unmasked MSISDN/IMSI CPNI leak.
- Toggle a defect on and demonstrate automated detection in tests.

### Step 4: AI Quality, RAG & Root Cause Analysis (RCA)
- Navigate to the **AI & RCA Assistant** sub-tab.
- Ask domain policy questions: `"What payment methods are supported?"` or `"What happens if 3DS fails?"`.
- Demonstrate:
  - Grounded context retrieval with chunk citations (`[AIRLINE-POLICY-01 / #chunk_0]`).
  - Real-time hallucination evaluation and groundedness scoring.
  - **DefectRCAAgent**: Run log analysis on a 3DS timeout signature to showcase automated error classification and recommended code remediation.

### Step 5: Multi-Signal Release Quality Gate Governance
- Navigate to the **Release Quality Gate** sub-tab.
- Explain multi-signal policy evaluation: combines test pass rate, critical defects, security findings, and AI groundedness metrics into an authoritative pass/block decision (`PRODUCTION_STRICT`, `STAGING_STANDARD`, `DEV_PR_FAST`).
- Inspect the persistent audit history table populated from PostgreSQL.

### Step 6: 11-Layer Test Pyramid Execution
- Showcase the local/CI automated test runner:
  ```powershell
  pytest -q
  # 367 passed in ~10s across unit, api, database, contract, regression, ai, rag, security, performance, agents, and multi-domain packs (427 total tests with Playwright E2E)
  ```
- Highlight engineering quality: explain why tests are fast, deterministic, and isolated.

### Step 7: Complete Portfolio Demonstration CLI (<300ms)
- Run the all-in-one portfolio demonstration:
  ```powershell
  python qa-engine/portfolio_demo.py
  # Orchestrates all 7 QE capabilities (Domains, Factories, Defects, RAG, Agents, Selector, Quality Gate)
  ```


## 8. Revision-Bound Release Verification

Every production release must bind the Git SHA, CI run, Vercel deployment, and actual serving revision before certification.

The live API exposes a read-only verification endpoint:

`GET /qa/release/serving-revision`

Required release evidence:

- exact Git merge SHA;
- successful main-branch CI run for that SHA;
- Vercel production deployment for that SHA;
- live `serving_sha` equal to the expected SHA;
- read-only production smoke checks pass;
- no required evidence is missing, stale, or contradictory.

A deployment marked READY by Vercel without a matching live serving revision is **not** sufficient for production certification.
