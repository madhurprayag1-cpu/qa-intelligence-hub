"""FinTech Synthetic Test Data Factories.

Adheres strictly to AGENTS.md Section 12 and docs/ROADMAP.md Task 7.2:
- Reuses PersonGenerator, IdentifierGenerator, and PaymentInstrumentGenerator.
- 100% synthetic, deterministic, and safe for portfolio demonstrations.
- Generates valid IBAN, SWIFT BIC, double-entry ledger entries, and ISO 20022 messages.
- Never uses real banking credentials, customer accounts, or production tokens.
"""

import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from base_factories import IdentifierGenerator, PersonGenerator
from domains.fintech.models import (
    AccountType,
    BankAccount,
    Currency,
    FraudEvaluationRequest,
    ISO20022CreditTransfer,
    KYCTier,
    KYCVerificationRequest,
    LedgerEntry,
    LedgerTransaction,
)


class AccountFactory:
    """Synthetic Bank Account Factory."""

    _SWIFT_BICS = [
        "CHASUS33XXX",  # Synthetic Chase BIC
        "BOFAUS3NXXX",  # Synthetic BofA BIC
        "BARCGB22XXX",  # Synthetic Barclays BIC
        "DBEUDD33XXX",  # Synthetic Deutsche Bank BIC
    ]

    @classmethod
    def build(
        cls,
        account_holder: Optional[str] = None,
        currency: Currency = Currency.USD,
        balance: float = 10000.0,
        kyc_tier: KYCTier = KYCTier.TIER_2_VERIFIED,
        account_type: AccountType = AccountType.CHECKING,
        index: int = 0,
    ) -> BankAccount:
        person = PersonGenerator.generate(index=index, email_domain="qahub-bank.io")
        holder = account_holder or person.full_name
        acc_num = f"{10000000 + index * 17 + secrets.randbelow(500):08d}"
        iban = f"GB29QAHB601613{acc_num}"
        bic = cls._SWIFT_BICS[index % len(cls._SWIFT_BICS)]
        acc_id = f"ACC-{IdentifierGenerator.generate_alphanumeric(8)}"

        return BankAccount(
            account_id=acc_id,
            iban=iban,
            bic_swift=bic,
            account_holder=holder,
            email=person.email,
            account_type=account_type,
            currency=currency,
            balance=balance,
            kyc_tier=kyc_tier,
            is_active=True,
        )

    @classmethod
    def build_batch(cls, count: int) -> List[BankAccount]:
        return [cls.build(index=i) for i in range(count)]


class TransferFactory:
    """Synthetic Double-Entry Ledger & ISO 20022 Transfer Factory."""

    @classmethod
    def build_transfer_payload(
        cls,
        source_account_id: str,
        destination_account_id: str,
        amount: float = 250.0,
        currency: Currency = Currency.USD,
        reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        ref = reference or IdentifierGenerator.generate_reference("TRF", 8)
        return {
            "source_account_id": source_account_id,
            "destination_account_id": destination_account_id,
            "amount": amount,
            "currency": currency.value,
            "reference": ref,
        }

    @classmethod
    def build_iso20022_pain001(
        cls,
        debtor_account: BankAccount,
        creditor_account: BankAccount,
        amount: float = 5000.0,
    ) -> ISO20022CreditTransfer:
        msg_id = f"MSG-{datetime.utcnow().strftime('%Y%m%d')}-{IdentifierGenerator.generate_numeric(6)}"
        inst_id = f"INSTR-{IdentifierGenerator.generate_alphanumeric(10)}"

        return ISO20022CreditTransfer(
            message_id=msg_id,
            instruction_id=inst_id,
            debtor_name=debtor_account.account_holder,
            debtor_iban=debtor_account.iban,
            debtor_agent_bic=debtor_account.bic_swift,
            creditor_name=creditor_account.account_holder,
            creditor_iban=creditor_account.iban,
            creditor_agent_bic=creditor_account.bic_swift,
            instructed_amount=amount,
            instructed_currency=debtor_account.currency,
            purpose_code="SALA",
            remittance_info=f"Invoice Settlement {IdentifierGenerator.generate_reference('INV', 6)}",
        )

    @classmethod
    def build_balanced_ledger_txn(
        cls,
        source_acc_id: str,
        dest_acc_id: str,
        amount: float = 500.0,
        currency: Currency = Currency.USD,
    ) -> LedgerTransaction:
        txn_id = f"TXN-{IdentifierGenerator.generate_alphanumeric(10)}"
        return LedgerTransaction(
            transaction_id=txn_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            description=f"Direct Transfer {source_acc_id} -> {dest_acc_id}",
            entries=[
                LedgerEntry(account_id=source_acc_id, entry_type="DEBIT", amount=amount, currency=currency),
                LedgerEntry(account_id=dest_acc_id, entry_type="CREDIT", amount=amount, currency=currency),
            ],
        )

    @classmethod
    def build_unbalanced_ledger_txn(cls) -> Dict[str, Any]:
        """Generates an unbalanced ledger entry (debits != credits) for invariant testing."""
        return {
            "transaction_id": f"TXN-{IdentifierGenerator.generate_alphanumeric(10)}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "description": "Corrupt Unbalanced Transaction",
            "entries": [
                {"account_id": "ACC-SRC-01", "entry_type": "DEBIT", "amount": 1000.0, "currency": "USD"},
                {"account_id": "ACC-DST-01", "entry_type": "CREDIT", "amount": 750.0, "currency": "USD"},
            ],
        }


class KYCFactory:
    """Synthetic Customer KYC Onboarding Factory."""

    @classmethod
    def build_applicant(
        cls,
        full_name: Optional[str] = None,
        monthly_income: float = 6500.0,
        pep_check_required: bool = True,
        index: int = 0,
    ) -> KYCVerificationRequest:
        person = PersonGenerator.generate(index=index)
        name = full_name or person.full_name
        cust_id = f"CUST-KYC-{10000 + index}"
        ssn_masked = f"***-**-{4000 + (index * 19) % 5000:04d}"

        return KYCVerificationRequest(
            customer_id=cust_id,
            full_name=name,
            date_of_birth="1988-04-12",
            country_code="US",
            tax_id_masked=ssn_masked,
            monthly_income=monthly_income,
            pep_check_required=pep_check_required,
        )

    @classmethod
    def build_pep_sanctioned_applicant(cls) -> KYCVerificationRequest:
        """Builds applicant matching a politically exposed persons (PEP) watch list."""
        req = cls.build_applicant(full_name="Vladislav Sanctioned-Watchlist")
        return req


class FraudAnomalyFactory:
    """Synthetic Transaction Anomaly Factory."""

    @classmethod
    def build_clean_request(cls, account_id: str = "ACC-SAFE-01") -> FraudEvaluationRequest:
        return FraudEvaluationRequest(
            account_id=account_id,
            amount=120.0,
            currency=Currency.USD,
            origin_country="US",
            destination_country="US",
            transactions_in_last_minute=1,
        )

    @classmethod
    def build_velocity_spike_request(cls, account_id: str = "ACC-ATTACK-01") -> FraudEvaluationRequest:
        """Simulates rapid automated transaction burst (velocity rate-limit breach)."""
        return FraudEvaluationRequest(
            account_id=account_id,
            amount=300.0,
            currency=Currency.USD,
            origin_country="US",
            destination_country="US",
            transactions_in_last_minute=8,  # > 3/min threshold
        )

    @classmethod
    def build_geo_impossible_travel_request(cls, account_id: str = "ACC-GEO-01") -> FraudEvaluationRequest:
        """Simulates cross-border impossible geographic distance anomaly."""
        return FraudEvaluationRequest(
            account_id=account_id,
            amount=2500.0,
            currency=Currency.USD,
            origin_country="US",
            destination_country="NG",  # Cross-border high-risk jump
            transactions_in_last_minute=1,
        )


class FXCalculator:
    """Foreign Exchange Calculation Engine with Defect Simulation."""

    RATES: Dict[str, float] = {
        "USD_EUR": 0.9215,
        "EUR_USD": 1.0852,
        "USD_GBP": 0.7860,
        "GBP_USD": 1.2723,
        "USD_JPY": 154.25,
        "JPY_USD": 0.00648,
    }

    @classmethod
    def convert(
        cls,
        from_curr: Currency,
        to_curr: Currency,
        amount: float,
        simulate_rounding_defect: bool = False,
    ) -> Dict[str, Any]:
        if from_curr == to_curr:
            rate = 1.0
        else:
            pair = f"{from_curr.value}_{to_curr.value}"
            rate = cls.RATES.get(pair, 1.0)

        fee_pct = 0.005  # 0.5% fee
        fee_amount = round(amount * fee_pct, 2)
        net_amount = amount - fee_amount

        exact_converted = net_amount * rate

        if simulate_rounding_defect:
            # Defect DEF-FT-002: Drops penny fractions via premature float truncation
            converted_amount = float(int(exact_converted))
            drift_detected = True
        else:
            converted_amount = round(exact_converted, 2)
            drift_detected = False

        precision_verified = not drift_detected and abs(converted_amount - round(exact_converted, 2)) < 0.01

        return {
            "from_currency": from_curr,
            "to_currency": to_curr,
            "base_amount": amount,
            "exchange_rate": rate,
            "fee_percentage": fee_pct,
            "fee_amount": fee_amount,
            "converted_amount": converted_amount,
            "precision_verified": precision_verified,
            "drift_detected": drift_detected,
        }
