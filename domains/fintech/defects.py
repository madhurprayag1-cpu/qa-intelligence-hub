"""FinTech Domain Defect Engineering Catalog.

Adheres strictly to AGENTS.md Section 9 and docs/ROADMAP.md Task 7.2:
- Explicit, documented, reproducible synthetic defect scenarios.
- Demonstrates senior SDET quality engineering detection capabilities in banking.
- Covers double-entry balance integrity, currency precision drift, KYC tier enforcement, fraud velocity bypass, and IDOR.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class FinTechDefectType(str, Enum):
    DOUBLE_DEBIT_RACE = "DOUBLE_DEBIT_RACE"
    PRECISION_ROUNDING_DRIFT = "PRECISION_ROUNDING_DRIFT"
    KYC_TIER_LIMIT_BYPASS = "KYC_TIER_LIMIT_BYPASS"
    FRAUD_VELOCITY_BYPASS = "FRAUD_VELOCITY_BYPASS"
    RAG_UNGROUNDED_FINANCIAL_ADVICE = "RAG_UNGROUNDED_FINANCIAL_ADVICE"
    IDOR_ACCOUNT_STATEMENT_ACCESS = "IDOR_ACCOUNT_STATEMENT_ACCESS"


@dataclass
class FinTechDefectDefinition:
    id: str
    code: str
    name: str
    category: str
    affected_endpoint: str
    description: str
    how_to_reproduce: str
    expected_qa_detection: str
    headers: Dict[str, str] = field(default_factory=dict)


FINTECH_DEFECT_REGISTRY: Dict[str, FinTechDefectDefinition] = {
    FinTechDefectType.DOUBLE_DEBIT_RACE.value: FinTechDefectDefinition(
        id=FinTechDefectType.DOUBLE_DEBIT_RACE.value,
        code="DEF-FT-001",
        name="Concurrent Transfer Double Debit / Balance Invariant Violation",
        category="Ledger Integrity & Concurrency",
        affected_endpoint="POST /fintech/transfers",
        description=(
            "Simulates a race condition where concurrent transfer executions bypass balance locking, "
            "debiting the source account multiple times and driving the available balance negative."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: DOUBLE_DEBIT_RACE' in POST /fintech/transfers.",
        expected_qa_detection=(
            "QA concurrency test validates source account balance >= 0; fails when balance is driven negative."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.DOUBLE_DEBIT_RACE.value},
    ),
    FinTechDefectType.PRECISION_ROUNDING_DRIFT.value: FinTechDefectDefinition(
        id=FinTechDefectType.PRECISION_ROUNDING_DRIFT.value,
        code="DEF-FT-002",
        name="Foreign Exchange Cent Rounding Drift",
        category="Financial Calculation Drift",
        affected_endpoint="POST /fintech/exchange/calculate",
        description=(
            "Simulates an arithmetic float truncation defect that drops penny decimal fractions during "
            "currency exchange conversion, violating GAAP financial precision rules."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: PRECISION_ROUNDING_DRIFT' in POST /fintech/exchange/calculate.",
        expected_qa_detection=(
            "QA precision test asserts converted_amount equals (base_amount - fee) * rate rounded to 2 decimal places; "
            "fails when cent discrepancy is detected."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.PRECISION_ROUNDING_DRIFT.value},
    ),
    FinTechDefectType.KYC_TIER_LIMIT_BYPASS.value: FinTechDefectDefinition(
        id=FinTechDefectType.KYC_TIER_LIMIT_BYPASS.value,
        code="DEF-FT-003",
        name="KYC Tier Daily Transfer Limit Bypass",
        category="Compliance & Regulatory Enforcement",
        affected_endpoint="POST /fintech/transfers",
        description=(
            "Allows a customer with Tier 1 Basic KYC (daily ceiling $1,000) to execute a transfer "
            "exceeding their allowed daily threshold without triggering verification escalation."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: KYC_TIER_LIMIT_BYPASS' in POST /fintech/transfers.",
        expected_qa_detection=(
            "QA compliance test asserts HTTP 403 / 422 for transfers exceeding tier limits; fails if HTTP 201 returned."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.KYC_TIER_LIMIT_BYPASS.value},
    ),
    FinTechDefectType.FRAUD_VELOCITY_BYPASS.value: FinTechDefectDefinition(
        id=FinTechDefectType.FRAUD_VELOCITY_BYPASS.value,
        code="DEF-FT-004",
        name="Real-Time Fraud Velocity Rate-Limiting Bypass",
        category="Fraud Prevention & Rate Limiting",
        affected_endpoint="POST /fintech/fraud/evaluate",
        description=(
            "Bypasses velocity rate-limiting rules, permitting an account with > 5 transactions/minute "
            "to receive an 'ALLOW' action instead of an automated challenge or block."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: FRAUD_VELOCITY_BYPASS' in POST /fintech/fraud/evaluate.",
        expected_qa_detection=(
            "QA fraud heuristic test asserts action in ['CHALLENGE_2FA', 'BLOCK'] for velocity > 3/min; fails if 'ALLOW' is returned."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.FRAUD_VELOCITY_BYPASS.value},
    ),
    FinTechDefectType.RAG_UNGROUNDED_FINANCIAL_ADVICE.value: FinTechDefectDefinition(
        id=FinTechDefectType.RAG_UNGROUNDED_FINANCIAL_ADVICE.value,
        code="DEF-FT-005",
        name="Ungrounded Financial Compliance / Tax Advice Claim",
        category="AI / RAG Safety & Regulatory Compliance",
        affected_endpoint="POST /ai/rag/query",
        description=(
            "Simulates RAG hallucination where model claims tax exemptions not grounded in statutory "
            "banking documents, violating financial advice compliance regulations."
        ),
        how_to_reproduce="Query RAG pipeline on financial topics with defect simulation active.",
        expected_qa_detection=(
            "QA RAG quality gate asserts groundedness >= 0.85; fails when ungrounded financial claims produce groundedness < 0.60."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.RAG_UNGROUNDED_FINANCIAL_ADVICE.value},
    ),
    FinTechDefectType.IDOR_ACCOUNT_STATEMENT_ACCESS.value: FinTechDefectDefinition(
        id=FinTechDefectType.IDOR_ACCOUNT_STATEMENT_ACCESS.value,
        code="DEF-FT-006",
        name="Insecure Direct Object Reference (IDOR) Bank Statement Access",
        category="Security & Authorization",
        affected_endpoint="GET /fintech/accounts/{account_id}",
        description=(
            "Allows an authenticated user to view balances and statements of accounts belonging to "
            "different customers without account ownership or admin authorization."
        ),
        how_to_reproduce="Include HTTP header 'X-Simulate-Defect: IDOR_ACCOUNT_STATEMENT_ACCESS' in GET /fintech/accounts/{account_id}.",
        expected_qa_detection=(
            "QA security test asserts HTTP 403 Forbidden for unauthorized account access; fails if HTTP 200 returned."
        ),
        headers={"X-Simulate-Defect": FinTechDefectType.IDOR_ACCOUNT_STATEMENT_ACCESS.value},
    ),
}
