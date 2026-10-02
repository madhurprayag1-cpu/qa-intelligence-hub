from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaymentMethod(str, Enum):
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    CREDIT_CARD_3DS = "CREDIT_CARD_3DS"
    DEBIT_CARD = "DEBIT_CARD"
    EASY_PAY = "EASY_PAY"
    UPI = "UPI"
    WALLET = "WALLET"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AUTHENTICATED = "AUTHENTICATED"
    PAID = "PAID"
    FAILED = "FAILED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class ThreeDSStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"),
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
    )

    method: Mapped[str] = mapped_column(
        String(30)
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=PaymentStatus.PENDING.value,
        index=True,
    )

    three_ds_required: Mapped[bool] = mapped_column(
        default=False
    )

    three_ds_status: Mapped[str] = mapped_column(
        String(30),
        default=ThreeDSStatus.NOT_REQUIRED.value,
    )

    authorization_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
    )

    transaction_reference: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )