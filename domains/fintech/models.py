"""FinTech & Digital Banking Pydantic Models & Financial Schemas.

Adheres strictly to AGENTS.md Sections 3, 8, 12, 13 and docs/ROADMAP.md Task 7.2:
- Double-entry bookkeeping ledger models (balance invariant: debits == credits).
- ISO 20022 SWIFT message models (pain.001 Credit Transfer & pacs.008 interbank).
- KYC verification tiers, PEP/AML sanctions screening, and transaction velocity fraud detection.
- PCI DSS 4.0 tokenized financial instruments and exchange rate precision models.
- 100% synthetic, public-safe financial data with zero real banking secrets.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CHF = "CHF"
    JPY = "JPY"


class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    ESCROW = "ESCROW"
    INVESTMENT = "INVESTMENT"


class KYCTier(str, Enum):
    TIER_1_BASIC = "TIER_1_BASIC"        # Limit $1,000 / day
    TIER_2_VERIFIED = "TIER_2_VERIFIED"  # Limit $25,000 / day
    TIER_3_ENHANCED = "TIER_3_ENHANCED"  # Unlimited with enhanced due diligence


class BankAccount(BaseModel):
    """Synthetic Bank Account Entity."""
    account_id: str = Field(pattern=r"^ACC-[A-Z0-9\-]{3,16}$")
    iban: str = Field(description="International Bank Account Number (synthetic)")
    bic_swift: str = Field(min_length=8, max_length=11, description="SWIFT BIC code")
    account_holder: str = Field(min_length=2)
    email: str
    account_type: AccountType = AccountType.CHECKING
    currency: Currency = Currency.USD
    balance: float = Field(ge=0.0, description="Available balance; never negative in standard operations")
    kyc_tier: KYCTier = KYCTier.TIER_2_VERIFIED
    is_active: bool = True


class LedgerEntry(BaseModel):
    """Double-entry bookkeeping atomic leg."""
    account_id: str
    entry_type: Literal["DEBIT", "CREDIT"]
    amount: float = Field(gt=0.0)
    currency: Currency = Currency.USD


class LedgerTransaction(BaseModel):
    """
    Atomic double-entry transaction record.
    Enforces foundational financial invariant: sum(debits) == sum(credits).
    """
    transaction_id: str = Field(pattern=r"^TXN-[A-Z0-9]{8,14}$")
    timestamp: str
    description: str
    entries: List[LedgerEntry] = Field(min_length=2)

    @field_validator("entries")
    @classmethod
    def validate_double_entry_balance(cls, entries: List[LedgerEntry]) -> List[LedgerEntry]:
        debits = sum(e.amount for e in entries if e.entry_type == "DEBIT")
        credits = sum(e.amount for e in entries if e.entry_type == "CREDIT")
        if abs(debits - credits) > 0.001:
            raise ValueError(
                f"Double-entry ledger invariant violated: Debits ({debits:.2f}) != Credits ({credits:.2f})"
            )
        return entries


class ISO20022CreditTransfer(BaseModel):
    """
    ISO 20022 pain.001.001.09 Customer Credit Transfer Initiation schema.
    Synthetic financial standard serialization.
    """
    message_id: str = Field(description="End-to-End message identification (e.g. MSG-20261001-001)")
    instruction_id: str
    debtor_name: str
    debtor_iban: str
    debtor_agent_bic: str
    creditor_name: str
    creditor_iban: str
    creditor_agent_bic: str
    instructed_amount: float = Field(gt=0.0)
    instructed_currency: Currency = Currency.USD
    purpose_code: str = Field(default="SALA", description="ISO 20022 4-character purpose code (e.g. SALA, INTE, TREA)")
    remittance_info: Optional[str] = "Synthetic B2B Settlement"


class KYCVerificationRequest(BaseModel):
    """Customer identity onboarding and AML verification request."""
    customer_id: str
    full_name: str
    date_of_birth: str
    country_code: str = "US"
    tax_id_masked: str = Field(description="Masked SSN/TIN (e.g. ***-**-4589)")
    monthly_income: float = Field(ge=0.0)
    pep_check_required: bool = True


class KYCVerificationResponse(BaseModel):
    """Customer identity onboarding verification result."""
    customer_id: str
    full_name: str
    assigned_tier: KYCTier
    daily_transfer_limit: float
    pep_sanctions_cleared: bool
    status: Literal["APPROVED", "MANUAL_REVIEW", "REJECTED"]
    review_reason: Optional[str] = None


class FraudEvaluationRequest(BaseModel):
    """Real-time transaction fraud evaluation request."""
    account_id: str
    amount: float = Field(gt=0.0)
    currency: Currency = Currency.USD
    origin_country: str = "US"
    destination_country: str = "US"
    transactions_in_last_minute: int = Field(ge=0)
    device_fingerprint: str = "dev_synth_default"


class FraudEvaluationResponse(BaseModel):
    """Fraud risk scoring and action response."""
    account_id: str
    risk_score: float = Field(ge=0.0, le=100.0, description="Risk score from 0.0 (clean) to 100.0 (fraud)")
    action: Literal["ALLOW", "CHALLENGE_2FA", "BLOCK"]
    detected_anomalies: List[str] = Field(default_factory=list)


class FXExchangeRequest(BaseModel):
    """Foreign exchange calculation request."""
    from_currency: Currency
    to_currency: Currency
    amount: float = Field(gt=0.0)


class FXExchangeResponse(BaseModel):
    """Foreign exchange calculation response."""
    from_currency: Currency
    to_currency: Currency
    base_amount: float
    exchange_rate: float
    fee_percentage: float = 0.005  # 0.5% fee
    fee_amount: float
    converted_amount: float
    precision_verified: bool
    drift_detected: bool = False
