# Domain Pack Extension Guide: Adding New Industry Domains

> **Core Portfolio Principle**:  
> *"Build the QA platform once. Plug in the domain. Reuse the engineering."*

The **QA Intelligence Hub** is engineered as a career-scale, domain-extensible Quality Engineering platform. Rather than building separate, disconnected test frameworks for different industries (e.g., Airline, Healthcare, E-commerce, Telecom, Banking/FinTech), the platform separates **domain-independent quality engineering capabilities** from **domain-specific business workflows**.

---

## 1. Architectural Model: Platform Core vs. Domain Packs

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          QA INTELLIGENCE HUB CORE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│ • Dynamic Domain Registry (domain_registry.py)                                  │
│ • Universal Playwright POM Core (BasePage.ts)                                   │
│ • Universal Synthetic Data Primitives (base_factories.py)                       │
│ • Domain-Aware Vector RAG Engine (rag.py with domain-scoping)                   │
│ • Provider-Agnostic AI Layer (Gemini, Claude, OpenAI, Mock)                     │
│ • Multi-Signal Release Quality Gate (quality_gate.py)                           │
│ • High-Concurrency Stress Benchmark Engine (load_generator.py)                  │
│ • Intelligent Regression Diff Impact Selector (regression_selector.py)          │
│ • Specialist QA Agents (SecurityTestingAgent, UIHealingAgent, ReportingAgent)   │
│ • Observability, Correlation Tracking & Auditing (ObservabilityMiddleware)      │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ plugs into
      ┌──────────────┬─────────────────┼─────────────────┬──────────────┐
      ▼              ▼                 ▼                 ▼              ▼
┌───────────┐  ┌───────────┐     ┌───────────┐     ┌───────────┐  ┌───────────┐
│  Airline  │  │Healthcare │     │  FinTech  │     │E-Commerce │  │  Telecom  │
│  / NDC    │  │  / FHIR   │     │ / Banking │     │  / Retail │  │ / 5G Mobile│
├───────────┤  ├───────────┤     ├───────────┤     ├───────────┤  ├───────────┤
│• Flight/3DS│ │• EHR/FHIR │     │• Ledger   │     │• Catalog  │  │• Plan/SIM │
│• Ancillary│  │• Dosage   │     │• ISO 20022│     │• Cart/FSM │  │• Rating/CDR│
│• Inventory│  │• HIPAA Sec│     │• KYC/AML  │     │• Refunds  │  │• Roaming  │
└───────────┘  └───────────┘     └───────────┘     └───────────┘  └───────────┘
```

---

## 2. What New Domains Automatically Inherit

When you plug a new domain into the QA Intelligence Hub, you **never** need to recreate:
1. **Playwright Engine**: Browser lifecycle, screenshot capture, auto-waits, ARIA accessibility lookups ([BasePage.ts](../tests/ui/core/BasePage.ts)).
2. **API Framework**: HTTP client tooling, auth injection, schema validation, latency assertions.
3. **Database Framework**: PostgreSQL transactions, foreign key constraints, connection poolers.
4. **AI & RAG Engine**: Semantic chunking, cosine vector similarity, hallucination detection, citation tracing ([rag.py](../ai-engine/rag.py)).
5. **Specialist Agents**: `SecurityTestingAgent` (SQLi, XSS, PCI DSS), `UIHealingAgent` (W3C ARIA self-healing), `ReportingAgent` (executive sign-offs).
6. **Quality Gate**: Multi-signal policy governance with configurable pass rates and defect limits.
7. **Performance Engine**: Concurrency queues, RPS throughput, p50/p90/p95/p99 distributions.
8. **CI/CD & Cloud Deployment**: GitHub Actions workflow, Docker Compose, Vercel Serverless, and Neon PostgreSQL.

---

## 3. Concrete Example: Adding "FinTech / Digital Banking" as Domain X

Here is the exact, zero-core-modification sequence for adding a hypothetical FinTech domain pack:

### Step 1: Create Domain Directory
```bash
mkdir -p domains/fintech
touch domains/fintech/__init__.py
```

### Step 2: Implement Domain Pack Definition (`domains/fintech/domain_pack.py`)
```python
from domain_registry import DomainCapability, DomainPack, domain_registry

fintech_domain_pack = DomainPack(
    domain_id="fintech",
    name="Digital Banking & Payments",
    version="1.0.0",
    description="Core ledger, double-entry bookkeeping, KYC onboarding, and SWIFT/SEPA transfers.",
    capabilities=[
        DomainCapability.API_TESTING,
        DomainCapability.DATABASE_TESTING,
        DomainCapability.SECURITY_AUDIT,
        DomainCapability.RAG_AI,
        DomainCapability.QUALITY_GATE,
    ],
    rag_sources=["FINTECH-POLICY-01", "KYC-AML-GUIDELINES"],
    defect_catalog={
        "DEF-FT-001": "DOUBLE_DEBIT_RACE: Concurrent transfers causing negative balance",
        "DEF-FT-002": "PRECISION_ROUNDING_ERROR: Cent rounding drift in interest calculation",
    },
    metadata={"regulatory_standard": "PCI DSS 4.0 / Basel III"},
)

# Auto-register with central registry
domain_registry.register(fintech_domain_pack)
```

### Step 3: Implement Domain Data Factories (`domains/fintech/factories.py`)
Reuse core primitives from `base_factories.py`:
```python
from base_factories import PersonGenerator, IdentifierGenerator, PaymentInstrumentGenerator

class AccountFactory:
    @classmethod
    def build_savings_account(cls, initial_balance: float = 1000.0):
        person = PersonGenerator.generate()
        return {
            "account_id": IdentifierGenerator.generate_reference("ACC", 10),
            "account_holder": person.full_name,
            "email": person.email,
            "iban": f"GB29NWBK601613{IdentifierGenerator.generate_numeric(8)}",
            "balance": initial_balance,
            "currency": "GBP",
        }
```

### Step 4: Implement Domain Regression Mappings (`domains/fintech/regression_map.py`)
```python
FINTECH_REGRESSION_PATTERNS = {
    "transfers": {
        "patterns": ["transfer", "ledger", "balance"],
        "tests": ["tests/api/test_transfers.py"],
        "tags": ["fintech", "payment", "database"],
        "ui_specs": ["tests/ui/transfer_flow.spec.ts"],
    },
}
```

### Step 5: Ingest Domain RAG Knowledge
Ingest policy documents tagged with `domain="fintech"`:
```python
from rag import RAGPipeline

pipeline = RAGPipeline()
pipeline.ingest_document(
    document_id="FINTECH-POLICY-01",
    text="International SWIFT wire transfers exceeding $10,000 trigger automated AML threshold checks.",
    domain="fintech",
)
```

### Step 6: Create Domain UI Page Objects Extending `BasePage`
```typescript
import { Page, Locator } from "@playwright/test";
import { BasePage } from "../core/BasePage";

export class TransferPage extends BasePage {
  readonly recipientInput: Locator;
  readonly amountInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    super(page);
    this.recipientInput = this.byTestId("recipient-account");
    this.amountInput = this.byTestId("transfer-amount");
    this.submitButton = this.byTestId("submit-transfer-btn");
  }

  async executeTransfer(recipient: string, amount: string) {
    await this.fillField(this.recipientInput, recipient);
    await this.fillField(this.amountInput, amount);
    await this.clickElement(this.submitButton);
  }
}
```

### Step 7: Select Active Domain via Environment
In terminal or CI/CD configuration:
```powershell
$env:QA_DOMAIN="fintech"
pytest tests/ -v
```

---

## 4. Verification Checklist for New Domains

- [ ] Domain Pack auto-registers in `domain_registry` without modifying `qa-engine/domain_registry.py`.
- [ ] Synthetic data generators inherit from `base_factories.py` and never contain confidential employer data.
- [ ] Domain RAG content is tagged with `domain="<domain_id>"` so vector searches stay cleanly isolated.
- [ ] UI Page Objects extend `tests/ui/core/BasePage.ts` for automated resilience.
- [ ] All 331 existing automated tests (314 pytest + 17 Playwright E2E) across domain packs continue to pass with zero regressions.
- [ ] Cloud deployment (Vercel Serverless + Neon PostgreSQL) executes without schema changes.
