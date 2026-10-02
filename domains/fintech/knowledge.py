"""Synthetic FinTech & Digital Banking QA Knowledge Base.

Adheres strictly to AGENTS.md Sections 8, 10, 18, 19 and docs/ROADMAP.md Task 7.2:
- 100% synthetic, public-safe banking and financial compliance knowledge documents.
- Strictly decoupled from reusable AI core and vector search indexers.
- Serves as the domain knowledge provider for multi-domain RAG retrieval and evaluation.
"""

from typing import Any, Dict, List


FINTECH_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    {
        "document_id": "FINTECH-LEDGER-01",
        "text": (
            "The digital core banking system strictly implements double-entry bookkeeping. Every financial transaction "
            "consists of at least two atomic legs: one debit and one credit. The total debit sum must exactly equal the total credit sum. "
            "Available balances for standard checking accounts are non-negative; any transaction resulting in negative available balance "
            "without pre-approved credit line must be rejected with an HTTP 409 Conflict. Atomic database locks guarantee that concurrent "
            "transfers cannot cause double debits or negative ledger drift."
        ),
        "metadata": {
            "title": "Double-Entry Ledger Principles & Balance Invariants",
            "domain": "fintech",
            "source": "FINTECH-LEDGER-01",
            "category": "ledger",
            "version": "1.0",
        },
    },
    {
        "document_id": "FINTECH-ISO20022-01",
        "text": (
            "Interbank and cross-border payments strictly adhere to the ISO 20022 messaging standard. The pain.001 message "
            "(Customer Credit Transfer Initiation) initiates payments from a debtor to a creditor. Mandatory attributes include "
            "debtor IBAN, creditor IBAN, receiving agent SWIFT BIC, instructed amount, currency, and a 4-character ISO purpose code "
            "(e.g., SALA for salary, INTE for interest). Transactions missing valid IBAN checksums or recognized BIC codes fail "
            "contract validation with HTTP 422 Unprocessable Entity."
        ),
        "metadata": {
            "title": "ISO 20022 SWIFT Messaging & pain.001 Credit Transfer Protocol",
            "domain": "fintech",
            "source": "FINTECH-ISO20022-01",
            "category": "standards",
            "version": "2022.1",
        },
    },
    {
        "document_id": "FINTECH-KYC-AML-01",
        "text": (
            "Customer onboarding enforces Anti-Money Laundering (AML) and Know Your Customer (KYC) compliance regulations. "
            "Onboarding is categorized into three verification tiers: Tier 1 Basic with a $1,000 daily transfer ceiling; Tier 2 Verified "
            "requiring tax identification and proof of address with a $25,000 daily limit; and Tier 3 Enhanced for corporate accounts. "
            "Any single transaction exceeding $10,000 triggers an automated Bank Secrecy Act (BSA) Currency Transaction Report (CTR) flag. "
            "Matches against Politically Exposed Persons (PEP) or OFAC sanctions watchlists require immediate transaction halt."
        ),
        "metadata": {
            "title": "KYC Onboarding Tiers & BSA/AML Sanctions Compliance",
            "domain": "fintech",
            "source": "FINTECH-KYC-AML-01",
            "category": "compliance",
            "version": "1.0",
        },
    },
    {
        "document_id": "FINTECH-FRAUD-01",
        "text": (
            "The real-time fraud detection engine evaluates transactions using automated risk scoring rules. "
            "A velocity threshold of more than 3 transactions within a 60-second window flags the account for automated challenge. "
            "Simultaneous transactions originating from geographically impossible distances (e.g. US to Nigeria within 5 minutes) "
            "trigger an immediate transaction block. Accounts flagged with high risk scores (> 75.0) are diverted to mandatory "
            "two-factor authentication (2FA) or fraud investigator queues."
        ),
        "metadata": {
            "title": "Real-Time Transaction Fraud Detection & Velocity Rules",
            "domain": "fintech",
            "source": "FINTECH-FRAUD-01",
            "category": "fraud",
            "version": "1.0",
        },
    },
    {
        "document_id": "FINTECH-PCIDSS-01",
        "text": (
            "All payment processing adheres strictly to PCI DSS 4.0 Requirement 3. Primary Account Numbers (PAN) must be masked "
            "to show only the first six and last four digits, or replaced with irreversible tokens. Sensitive Authentication Data (SAD), "
            "including card validation values (CVV/CVC) and full magnetic stripe data, must never be stored post-authorization under any "
            "circumstances. Cryptographic keys for tokenized payment storage must be rotated every 12 months."
        ),
        "metadata": {
            "title": "PCI DSS 4.0 Tokenization & Cardholder Data Protection",
            "domain": "fintech",
            "source": "FINTECH-PCIDSS-01",
            "category": "security",
            "version": "4.0",
        },
    },
]


def get_fintech_knowledge_docs() -> List[Dict[str, Any]]:
    """Provider function returning synthetic knowledge documents for the FinTech domain pack."""
    return FINTECH_KNOWLEDGE_DOCS
