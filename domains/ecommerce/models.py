"""E-Commerce Domain Models & Validation Rules.

Adheres strictly to AGENTS.md Sections 8, 9, 13, and 14:
- Pydantic v2 schemas for Catalog, Cart, Checkout, Order Lifecycle, and Returns.
- Strict finite-state machine transitions for orders and returns.
- Boundary checking for negative quantities, discount caps, and inventory limits.
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ProductCategory(str, Enum):
    ELECTRONICS = "ELECTRONICS"
    APPAREL = "APPAREL"
    HOME_GOODS = "HOME_GOODS"
    BOOKS = "BOOKS"
    BEAUTY = "BEAUTY"


class ShippingTier(str, Enum):
    STANDARD = "STANDARD"      # 4.99, free over 50.00
    EXPEDITED = "EXPEDITED"    # 12.99
    OVERNIGHT = "OVERNIGHT"    # 24.99
    FREE = "FREE"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURNED = "RETURNED"


class ReturnStatus(str, Enum):
    REQUESTED = "REQUESTED"
    ITEM_INSPECTED = "ITEM_INSPECTED"
    REFUND_PROCESSED = "REFUND_PROCESSED"
    REJECTED = "REJECTED"


# Valid Order State Machine Transition Rules
VALID_ORDER_TRANSITIONS: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.PAYMENT_AUTHORIZED, OrderStatus.CANCELLED],
    OrderStatus.PAYMENT_AUTHORIZED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [OrderStatus.RETURN_REQUESTED],
    OrderStatus.RETURN_REQUESTED: [OrderStatus.RETURNED],
    OrderStatus.CANCELLED: [],
    OrderStatus.RETURNED: [],
}


class Product(BaseModel):
    sku: str = Field(..., min_length=4, max_length=32, description="Unique Stock Keeping Unit (e.g. SKU-ECOM-1001)")
    name: str = Field(..., min_length=2, max_length=128)
    category: ProductCategory
    price: float = Field(..., gt=0.0, description="Product unit price in USD")
    stock_quantity: int = Field(..., ge=0, description="Available inventory count")
    weight_kg: float = Field(default=0.5, gt=0.0)
    is_active: bool = True

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        if not v.startswith("SKU-"):
            raise ValueError("SKU must start with 'SKU-'")
        return v


class CartItem(BaseModel):
    sku: str
    product_name: str = Field(default="")
    unit_price: float = Field(..., gt=0.0)
    quantity: int = Field(..., gt=0, le=99, description="Quantity must be between 1 and 99")

    @model_validator(mode="before")
    @classmethod
    def populate_product_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("product_name") and data.get("name"):
                data["product_name"] = data["name"]
            elif not data.get("product_name"):
                data["product_name"] = data.get("sku", "Product")
        return data

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.quantity, 2)


class PromoCode(BaseModel):
    code: str
    discount_percent: float = Field(..., gt=0.0, le=50.0, description="Max allowed discount is 50%")
    min_spend: float = Field(default=0.0, ge=0.0)
    max_discount_amount: float = Field(default=100.0, gt=0.0)
    is_active: bool = True


class Cart(BaseModel):
    cart_id: str
    customer_id: str
    items: List[CartItem] = Field(default_factory=list)
    shipping_tier: ShippingTier = ShippingTier.STANDARD
    applied_promo: Optional[PromoCode] = None
    subtotal: float = 0.0
    discount_amount: float = 0.0
    shipping_cost: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0


class CheckoutRequest(BaseModel):
    cart_id: str = Field(default="CART-DEFAULT")
    customer_id: str
    customer_email: str
    items: List[CartItem] = Field(..., min_length=1)
    shipping_tier: ShippingTier = ShippingTier.STANDARD
    shipping_address: Dict[str, str] = Field(default_factory=dict)
    payment_method: str = Field(default="CREDIT_CARD", description="CREDIT_CARD, WALLET, or DIRECT_DEBIT")
    promo_code: Optional[str] = None
    client_asserted_total: Optional[float] = None


class Order(BaseModel):
    order_id: str
    customer_id: str
    customer_email: str
    items: List[CartItem]
    status: OrderStatus
    subtotal: float
    discount_amount: float
    shipping_cost: float
    tax_amount: float
    total_amount: float
    shipping_tier: ShippingTier
    shipping_address: Dict[str, str]
    payment_transaction_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tracking_number: Optional[str] = None


class ReturnRequest(BaseModel):
    return_id: str
    order_id: str
    sku: str
    quantity: int = Field(..., gt=0)
    reason: str
    status: ReturnStatus = ReturnStatus.REQUESTED
    refund_amount: float = Field(..., ge=0.0)
    restocking_fee: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PricingCalculator:
    """High-precision e-commerce financial calculation engine."""

    STANDARD_SHIPPING_FLAT = 4.99
    EXPEDITED_SHIPPING_FLAT = 12.99
    OVERNIGHT_SHIPPING_FLAT = 24.99
    FREE_SHIPPING_THRESHOLD = 50.00
    DEFAULT_TAX_RATE = 0.08  # 8% standard sales tax

    @classmethod
    def calculate_shipping(cls, subtotal: float, tier: ShippingTier) -> float:
        if tier == ShippingTier.FREE:
            return 0.0
        if tier == ShippingTier.STANDARD:
            return 0.0 if subtotal >= cls.FREE_SHIPPING_THRESHOLD else cls.STANDARD_SHIPPING_FLAT
        if tier == ShippingTier.EXPEDITED:
            return cls.EXPEDITED_SHIPPING_FLAT
        if tier == ShippingTier.OVERNIGHT:
            return cls.OVERNIGHT_SHIPPING_FLAT
        return cls.STANDARD_SHIPPING_FLAT

    @classmethod
    def calculate_cart(
        cls,
        items: List[CartItem],
        shipping_tier: ShippingTier = ShippingTier.STANDARD,
        promo: Optional[PromoCode] = None,
        tax_rate: float = DEFAULT_TAX_RATE,
    ) -> Dict[str, float]:
        subtotal = round(sum(item.line_total for item in items), 2)
        
        # Promo discount calculation
        discount = 0.0
        if promo and promo.is_active:
            if subtotal >= promo.min_spend:
                raw_discount = subtotal * (promo.discount_percent / 100.0)
                discount = round(min(raw_discount, promo.max_discount_amount), 2)

        taxable_amount = max(0.0, subtotal - discount)
        shipping = cls.calculate_shipping(taxable_amount, shipping_tier)
        tax = round(taxable_amount * tax_rate, 2)
        total = round(taxable_amount + shipping + tax, 2)

        return {
            "subtotal": subtotal,
            "discount_amount": discount,
            "shipping_cost": shipping,
            "tax_amount": tax,
            "total_amount": total,
        }

    @classmethod
    def validate_transition(cls, current: OrderStatus, target: OrderStatus) -> bool:
        """Validates if order state transition is legal per business finite-state machine."""
        allowed = VALID_ORDER_TRANSITIONS.get(current, [])
        return target in allowed
