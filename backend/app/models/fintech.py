from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class FinTechAccountModel(Base):
    """Persistent storage for FinTech Bank Accounts."""
    __tablename__ = "fintech_accounts"

    account_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    iban: Mapped[str] = mapped_column(String(34), unique=True, index=True, nullable=False)
    bic_swift: Mapped[str] = mapped_column(String(11), nullable=False)
    account_holder: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), default="CHECKING")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    kyc_tier: Mapped[str] = mapped_column(String(30), default="TIER_2_VERIFIED")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinTechTransactionModel(Base):
    """Persistent storage for double-entry transactions."""
    __tablename__ = "fintech_transactions"

    transaction_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_account_id: Mapped[str] = mapped_column(
        ForeignKey("fintech_accounts.account_id"),
        index=True,
        nullable=False,
    )
    destination_account_id: Mapped[str] = mapped_column(
        ForeignKey("fintech_accounts.account_id"),
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SETTLED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
