from decimal import Decimal
from datetime import date

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, ThreeDSStatus


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)

    method: PaymentMethod

    three_ds_result: ThreeDSStatus = ThreeDSStatus.NOT_REQUIRED


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: Decimal
    currency: str
    method: str
    status: str
    three_ds_required: bool
    three_ds_status: str
    authorization_status: str
    transaction_reference: str | None
    provider_reference: str | None
    failure_code: str | None
    failure_reason: str | None
    retry_count: int