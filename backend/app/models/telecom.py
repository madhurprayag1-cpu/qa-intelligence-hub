from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class TelecomSubscriberModel(Base):
    """Persistent storage for Telecom mobile subscriber lines."""
    __tablename__ = "telecom_subscribers"

    subscriber_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    msisdn: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    iccid: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    imsi: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    minutes_used: Mapped[int] = mapped_column(Integer, default=0)
    sms_used: Mapped[int] = mapped_column(Integer, default=0)
    data_used_mb: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    roaming_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TelecomCDRModel(Base):
    """Persistent storage for rated Call Detail Records."""
    __tablename__ = "telecom_cdrs"

    cdr_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    msisdn: Mapped[str] = mapped_column(
        ForeignKey("telecom_subscribers.msisdn", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    destination: Mapped[str] = mapped_column(String(50), nullable=False)
    call_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(30), default="domestic")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    bytes_transferred: Mapped[int] = mapped_column(Integer, default=0)
    rated_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    billed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
