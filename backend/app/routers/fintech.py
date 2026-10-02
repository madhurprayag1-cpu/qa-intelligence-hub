"""FinTech & Digital Banking REST API & SUT Router.

Adheres strictly to AGENTS.md Sections 8, 9, 13, 21 and Phase 1B Blueprint:
- Production-grade synthetic SUT endpoints for Bank Accounts, Double-Entry Transfers, ISO 20022 SWIFT, KYC/AML, and Fraud Detection.
- Dual-plane execution: PostgreSQL persistence via SQLAlchemy models + in-memory hermetic cache.
- Strict tenant isolation with owner_user_id enforcing IDOR boundaries.
- Realistic defect injection hooks for QA demonstration (DEF-FT-001 through DEF-FT-006).
"""

from datetime import datetime
from decimal import Decimal
import secrets
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import User, get_current_domain_user
from app.db.database import get_db
from app.models.fintech import FinTechAccountModel, FinTechTransactionModel
from domains.fintech.defects import FINTECH_DEFECT_REGISTRY, FinTechDefectType
from domains.fintech.factories import FXCalculator
from domains.fintech.models import (
    AccountType,
    BankAccount,
    Currency,
    FraudEvaluationRequest,
    FraudEvaluationResponse,
    FXExchangeRequest,
    FXExchangeResponse,
    ISO20022CreditTransfer,
    KYCTier,
    KYCVerificationRequest,
    KYCVerificationResponse,
    LedgerEntry,
    LedgerTransaction,
)

router = APIRouter(prefix="/fintech", tags=["fintech-domain"])

# Hermetic in-memory store for synthetic FinTech SUT execution
_ACCOUNT_STORE: Dict[str, BankAccount] = {}
_TRANSACTION_STORE: List[Dict[str, Any]] = []


def reset_fintech_store() -> None:
    """Resets in-memory stores and seeds baseline synthetic accounts for hermetic test execution."""
    _ACCOUNT_STORE.clear()
    _TRANSACTION_STORE.clear()

    # Seed baseline synthetic accounts
    acc1 = BankAccount(
        account_id="ACC-FT-001",
        account_holder="Alex Vance",
        email="alex.vance@example.org",
        iban="US89370400440532013000",
        bic_swift="CHASUS33XXX",
        currency=Currency.USD,
        balance=10000.0,
        account_type=AccountType.CHECKING,
        kyc_tier=KYCTier.TIER_2_VERIFIED,
        is_active=True,
    )
    acc2 = BankAccount(
        account_id="ACC-FT-002",
        account_holder="Morgan Stanley Corp",
        email="treasury@morgan.example",
        iban="US99370400440532019999",
        bic_swift="CITIUS33XXX",
        currency=Currency.USD,
        balance=25000.0,
        account_type=AccountType.ESCROW,
        kyc_tier=KYCTier.TIER_3_ENHANCED,
        is_active=True,
    )
    _ACCOUNT_STORE[acc1.account_id] = acc1
    _ACCOUNT_STORE[acc2.account_id] = acc2


# Seed baseline accounts on module load
reset_fintech_store()


@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=BankAccount)
async def create_account(
    account: BankAccount,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> BankAccount:
    """Creates a new synthetic bank account and persists to PostgreSQL with tenant isolation."""
    _ACCOUNT_STORE[account.account_id] = account

    # DB Persistence
    try:
        existing = db.get(FinTechAccountModel, account.account_id)
        if existing:
            existing.balance = Decimal(str(account.balance))
            existing.is_active = account.is_active
        else:
            db_acc = FinTechAccountModel(
                account_id=account.account_id,
                owner_user_id=current_user.id,
                iban=account.iban,
                bic_swift=account.bic_swift,
                account_holder=account.account_holder,
                email=account.email,
                account_type=account.account_type.value if hasattr(account.account_type, "value") else str(account.account_type),
                currency=account.currency.value if hasattr(account.currency, "value") else str(account.currency),
                balance=Decimal(str(account.balance)),
                kyc_tier=account.kyc_tier.value if hasattr(account.kyc_tier, "value") else str(account.kyc_tier),
                is_active=account.is_active,
            )
            db.add(db_acc)
        db.commit()
    except Exception:
        db.rollback()

    return account


@router.get("/accounts", response_model=List[BankAccount])
async def list_accounts(
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[BankAccount]:
    """Lists accounts owned by the authenticated customer."""
    try:
        if current_user.role in {"admin", "staff"}:
            db_accounts = db.query(FinTechAccountModel).all()
        else:
            db_accounts = (
                db.query(FinTechAccountModel)
                .filter(FinTechAccountModel.owner_user_id == current_user.id)
                .all()
            )
        if db_accounts:
            results = []
            for a in db_accounts:
                mem = _ACCOUNT_STORE.get(a.account_id)
                if mem:
                    results.append(mem)
                else:
                    results.append(
                        BankAccount(
                            account_id=a.account_id,
                            account_holder=a.account_holder,
                            email=a.email,
                            iban=a.iban,
                            bic_swift=a.bic_swift,
                            currency=Currency(a.currency),
                            balance=float(a.balance),
                            account_type=AccountType(a.account_type) if a.account_type in [t.value for t in AccountType] else AccountType.CHECKING,
                            kyc_tier=KYCTier(a.kyc_tier) if a.kyc_tier in [t.value for t in KYCTier] else KYCTier.TIER_1_BASIC,
                            is_active=a.is_active,
                        )
                    )
            return results
    except Exception:
        pass

    return list(_ACCOUNT_STORE.values())


@router.get("/accounts/{account_id}", response_model=BankAccount)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(default="account_owner", alias="X-User-Role"),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> BankAccount:
    """
    Retrieves account details and available balance.
    Supports defect simulation:
    - IDOR_ACCOUNT_STATEMENT_ACCESS: Bypasses account authorization checks.
    """
    account = _ACCOUNT_STORE.get(account_id)
    db_acc = None
    try:
        db_acc = db.get(FinTechAccountModel, account_id)
    except Exception:
        pass

    if not account and not db_acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank account '{account_id}' not found.",
        )

    is_idor_defect = x_simulate_defect in (
        FinTechDefectType.IDOR_ACCOUNT_STATEMENT_ACCESS.value,
        "IDOR_ACCOUNT_STATEMENT_ACCESS",
        "IDOR_STATEMENT_LEAK",
        "DEF-FT-006",
    )
    if not is_idor_defect:
        effective_role = current_user.role if current_user.role != "passenger" else x_user_role
        if effective_role in ["unauthorized", "guest", "foreign_user"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: User not authorized to view requested bank account statement.",
            )

        # IDOR tenant boundary enforcement
        if db_acc and current_user.role not in {"admin", "staff"}:
            if db_acc.owner_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: IDOR protection prevented access to another customer's bank account.",
                )

    if account:
        return account

    return BankAccount(
        account_id=db_acc.account_id,
        account_holder=db_acc.account_holder,
        email=db_acc.email,
        iban=db_acc.iban,
        bic_swift=db_acc.bic_swift,
        currency=Currency(db_acc.currency),
        balance=float(db_acc.balance),
        account_type=AccountType(db_acc.account_type) if db_acc.account_type in [t.value for t in AccountType] else AccountType.CHECKING,
        kyc_tier=KYCTier(db_acc.kyc_tier) if db_acc.kyc_tier in [t.value for t in KYCTier] else KYCTier.TIER_1_BASIC,
        is_active=db_acc.is_active,
    )


@router.get("/transactions/{account_id}")
async def list_transactions_for_account(
    account_id: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves transaction history for an account statement with IDOR verification."""
    try:
        db_acc = db.get(FinTechAccountModel, account_id)
        if db_acc and current_user.role not in {"admin", "staff"}:
            if db_acc.owner_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: IDOR protection prevented access to another account's transactions.",
                )

        db_txns = (
            db.query(FinTechTransactionModel)
            .filter(
                (FinTechTransactionModel.source_account_id == account_id)
                | (FinTechTransactionModel.destination_account_id == account_id)
            )
            .order_by(FinTechTransactionModel.created_at.desc())
            .all()
        )
        if db_txns:
            return [
                {
                    "transaction_id": t.transaction_id,
                    "source_account_id": t.source_account_id,
                    "destination_account_id": t.destination_account_id,
                    "amount": float(t.amount),
                    "currency": t.currency,
                    "description": t.description,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                }
                for t in db_txns
            ]
    except HTTPException:
        raise
    except Exception:
        pass

    return [
        t for t in _TRANSACTION_STORE
        if t.get("source_account_id") == account_id or t.get("destination_account_id") == account_id
    ]


@router.post("/transfers", status_code=status.HTTP_201_CREATED)
async def execute_transfer(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Executes an atomic double-entry fund transfer between two accounts.
    Persists ledger mutations to PostgreSQL.
    Supports defect simulation:
    - DOUBLE_DEBIT_RACE: Bypasses balance locking, debiting double the amount and driving balance negative.
    - KYC_TIER_LIMIT_BYPASS: Permits transfer amounts exceeding customer KYC daily limit.
    """
    src_id = payload.get("source_account_id")
    dst_id = payload.get("destination_account_id")
    amount = float(payload.get("amount", 0.0))

    if not src_id or not dst_id or amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid transfer parameters: source, destination, and positive amount required.",
        )

    source = _ACCOUNT_STORE.get(src_id)
    dest = _ACCOUNT_STORE.get(dst_id)

    if not source:
        db_src = db.get(FinTechAccountModel, src_id)
        if db_src:
            source = BankAccount(
                account_id=db_src.account_id,
                account_holder=db_src.account_holder,
                email=db_src.email,
                iban=db_src.iban,
                bic_swift=db_src.bic_swift,
                currency=Currency(db_src.currency),
                balance=float(db_src.balance),
                account_type=AccountType.CHECKING,
                kyc_tier=KYCTier(db_src.kyc_tier) if db_src.kyc_tier in [t.value for t in KYCTier] else KYCTier.TIER_1_BASIC,
            )
            _ACCOUNT_STORE[src_id] = source

    if not dest:
        db_dst = db.get(FinTechAccountModel, dst_id)
        if db_dst:
            dest = BankAccount(
                account_id=db_dst.account_id,
                account_holder=db_dst.account_holder,
                email=db_dst.email,
                iban=db_dst.iban,
                bic_swift=db_dst.bic_swift,
                currency=Currency(db_dst.currency),
                balance=float(db_dst.balance),
                account_type=AccountType.CHECKING,
                kyc_tier=KYCTier(db_dst.kyc_tier) if db_dst.kyc_tier in [t.value for t in KYCTier] else KYCTier.TIER_1_BASIC,
            )
            _ACCOUNT_STORE[dst_id] = dest

    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source account '{src_id}' not found.")
    if not dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination account '{dst_id}' not found.")

    is_kyc_defect = x_simulate_defect in (
        FinTechDefectType.KYC_TIER_LIMIT_BYPASS.value,
        "KYC_TIER_LIMIT_BYPASS",
        "DEF-FT-002",
    )
    is_double_debit_defect = x_simulate_defect in (
        FinTechDefectType.DOUBLE_DEBIT_RACE.value,
        "DOUBLE_DEBIT_RACE",
        "DEF-FT-001",
    )

    # KYC Tier Limit Verification
    tier_limits = {
        KYCTier.TIER_1_BASIC: 1000.0,
        KYCTier.TIER_2_VERIFIED: 25000.0,
        KYCTier.TIER_3_ENHANCED: float("inf"),
    }
    max_limit = tier_limits.get(source.kyc_tier, 1000.0)

    if not is_kyc_defect and amount > max_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transfer amount ${amount:.2f} exceeds KYC daily limit of ${max_limit:.2f} for tier '{source.kyc_tier.value}'.",
        )

    # Balance Verification
    if not is_double_debit_defect and source.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient funds: available balance ${source.balance:.2f} is less than transfer amount ${amount:.2f}.",
        )

    # Execute Ledger Mutation in-memory
    if is_double_debit_defect:
        source.balance -= (amount * 2)
        dest.balance += amount
    else:
        source.balance -= amount
        dest.balance += amount

    txn_id = f"TXN-{secrets.token_hex(4).upper()}"
    txn_record = {
        "transaction_id": txn_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_account_id": src_id,
        "destination_account_id": dst_id,
        "amount": amount,
        "currency": source.currency.value,
        "source_new_balance": source.balance,
        "dest_new_balance": dest.balance,
        "status": "SETTLED",
    }
    _TRANSACTION_STORE.append(txn_record)

    # DB Persistence
    try:
        db_src = db.get(FinTechAccountModel, src_id)
        db_dst = db.get(FinTechAccountModel, dst_id)
        if db_src:
            db_src.balance = Decimal(str(source.balance))
        if db_dst:
            db_dst.balance = Decimal(str(dest.balance))

        if db_src and db_dst:
            db_txn = FinTechTransactionModel(
                transaction_id=txn_id,
                source_account_id=src_id,
                destination_account_id=dst_id,
                amount=Decimal(str(amount)),
                currency=source.currency.value,
                description=f"Transfer to {dst_id}",
                status="SETTLED",
            )
            db.add(db_txn)
        db.commit()
    except Exception:
        db.rollback()

    return txn_record


@router.post("/transfers/swift", status_code=status.HTTP_201_CREATED)
async def submit_swift_pain001(transfer: ISO20022CreditTransfer) -> Dict[str, Any]:
    """Processes an ISO 20022 pain.001 Credit Transfer Initiation message."""
    if len(transfer.debtor_iban) < 15 or len(transfer.creditor_iban) < 15:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ISO 20022 validation error: IBAN must contain at least 15 alphanumeric characters.",
        )

    return {
        "message_id": transfer.message_id,
        "instruction_id": transfer.instruction_id,
        "status": "ACCEPTED_SETTLEMENT_IN_PROCESS",
        "iso_standard": "pain.001.001.09",
        "amount": transfer.instructed_amount,
        "currency": transfer.instructed_currency.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/kyc/verify", response_model=KYCVerificationResponse)
async def verify_kyc_applicant(request: KYCVerificationRequest) -> KYCVerificationResponse:
    """Evaluates customer identity onboarding and AML sanctions risk."""
    is_sanctioned = "sanctioned" in request.full_name.lower() or "blocked" in request.full_name.lower()

    if is_sanctioned:
        return KYCVerificationResponse(
            customer_id=request.customer_id,
            full_name=request.full_name,
            assigned_tier=KYCTier.TIER_1_BASIC,
            daily_transfer_limit=0.0,
            pep_sanctions_cleared=False,
            status="REJECTED",
            review_reason="OFAC / PEP Sanctions Watchlist Match Detected",
        )

    # Tier assignment based on income verification
    if request.monthly_income >= 5000.0:
        tier = KYCTier.TIER_2_VERIFIED
        limit = 25000.0
    else:
        tier = KYCTier.TIER_1_BASIC
        limit = 1000.0

    return KYCVerificationResponse(
        customer_id=request.customer_id,
        full_name=request.full_name,
        assigned_tier=tier,
        daily_transfer_limit=limit,
        pep_sanctions_cleared=True,
        status="APPROVED",
    )


@router.post("/fraud/evaluate", response_model=FraudEvaluationResponse)
async def evaluate_fraud_risk(
    request: FraudEvaluationRequest,
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> FraudEvaluationResponse:
    """
    Evaluates real-time transaction risk using automated velocity and geographic rules.
    Supports defect simulation:
    - FRAUD_VELOCITY_BYPASS: Bypasses rate-limiting and approves high velocity attacks.
    """
    is_velocity_bypass = x_simulate_defect in (
        FinTechDefectType.FRAUD_VELOCITY_BYPASS.value,
        "FRAUD_VELOCITY_BYPASS",
        "FRAUD_VELOCITY_RULE_EVASION",
        "DEF-FT-004",
    )

    anomalies: List[str] = []
    risk_score = 5.0
    action: Literal["ALLOW", "CHALLENGE_2FA", "BLOCK"] = "ALLOW"

    # Rule 1: High Velocity Burst (> 3 txns / minute)
    if request.transactions_in_last_minute > 3:
        if not is_velocity_bypass:
            anomalies.append("VELOCITY_SPIKE_EXCEEDED")
            risk_score += 75.0
            action = "CHALLENGE_2FA"

    # Rule 2: Cross-Border Geolocation Anomaly
    high_risk_corridors = [("US", "NG"), ("US", "KP"), ("US", "RU")]
    corridor = (request.origin_country, request.destination_country)
    if corridor in high_risk_corridors:
        anomalies.append("IMPOSSIBLE_TRAVEL_DISTANCE")
        risk_score += 90.0
        action = "BLOCK"

    # Rule 3: High Value AML Reporting Threshold ($10,000)
    if request.amount >= 10000.0:
        anomalies.append("BSA_AML_REPORTING_THRESHOLD")
        if action != "BLOCK":
            risk_score = max(risk_score, 60.0)
            action = "CHALLENGE_2FA"

    risk_score = min(100.0, risk_score)
    return FraudEvaluationResponse(
        account_id=request.account_id,
        risk_score=risk_score,
        action=action,
        detected_anomalies=anomalies,
    )


@router.post("/exchange/calculate", response_model=FXExchangeResponse)
async def calculate_fx_exchange(
    request: FXExchangeRequest,
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> FXExchangeResponse:
    """
    Calculates foreign exchange currency conversion.
    Supports defect simulation:
    - PRECISION_ROUNDING_DRIFT: Injects floating-point cent truncation defect.
    """
    is_rounding_defect = x_simulate_defect == FinTechDefectType.PRECISION_ROUNDING_DRIFT.value
    res = FXCalculator.convert(
        from_curr=request.from_currency,
        to_curr=request.to_currency,
        amount=request.amount,
        simulate_rounding_defect=is_rounding_defect,
    )

    return FXExchangeResponse(
        from_currency=res["from_currency"],
        to_currency=res["to_currency"],
        base_amount=res["base_amount"],
        exchange_rate=res["exchange_rate"],
        fee_percentage=res["fee_percentage"],
        fee_amount=res["fee_amount"],
        converted_amount=res["converted_amount"],
        precision_verified=res["precision_verified"],
        drift_detected=res["drift_detected"],
    )


@router.get("/defects")
async def list_fintech_defects() -> List[Dict[str, Any]]:
    """Returns documentation and simulation instructions for FinTech defect scenarios."""
    return [
        {
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "affected_endpoint": d.affected_endpoint,
            "description": d.description,
            "how_to_reproduce": d.how_to_reproduce,
            "expected_qa_detection": d.expected_qa_detection,
            "headers": d.headers,
        }
        for d in FINTECH_DEFECT_REGISTRY.values()
    ]
