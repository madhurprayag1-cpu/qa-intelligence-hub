"""E-Commerce Domain Defect Catalog & Simulation Definitions.

Adheres strictly to AGENTS.md Section 9 and Master Architecture Directive:
- Documents 6 reproducible, realistic defects in enterprise e-commerce platforms.
- Demonstrates QA detection across inventory race conditions, financial pricing tampering,
  discount stacking, state machine desync, stale cache drift, and duplicate refund credits.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class EcommerceDefectType(str, Enum):
    OVERSELLING_RACE = "DEF-EC-001"
    PROMO_STACKING_EXPLOIT = "DEF-EC-002"
    PRICE_TAMPERING_INJECTION = "DEF-EC-003"
    ORDER_STATE_DESYNC = "DEF-EC-004"
    STALE_CART_INVENTORY = "DEF-EC-005"
    REFUND_DOUBLE_CREDIT = "DEF-EC-006"


@dataclass
class EcommerceDefectDefinition:
    code: str
    name: str
    category: str
    affected_endpoint: str
    description: str
    how_to_reproduce: str
    expected_qa_detection: str
    headers: Dict[str, str] = field(default_factory=dict)


ECOMMERCE_DEFECT_REGISTRY: Dict[str, EcommerceDefectDefinition] = {
    EcommerceDefectType.OVERSELLING_RACE.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.OVERSELLING_RACE.value,
        name="Flash Sale Overselling Concurrency Race",
        category="Concurrency & Inventory Invariants",
        affected_endpoint="POST /ecommerce/checkout",
        description=(
            "Simulates high-concurrency checkout race condition where stock availability "
            "locks are bypassed, allowing remaining product inventory to drop below zero."
        ),
        how_to_reproduce="Send HTTP header 'X-Simulate-Defect: DEF-EC-001' during concurrent checkout requests.",
        expected_qa_detection=(
            "QA concurrency test asserts inventory >= 0. Invariant fails with "
            "InventoryOversoldError when stock is driven negative."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.OVERSELLING_RACE.value},
    ),
    EcommerceDefectType.PROMO_STACKING_EXPLOIT.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.PROMO_STACKING_EXPLOIT.value,
        name="Discount Promo Code Stacking Exploit",
        category="Financial Reconciliation & Pricing",
        affected_endpoint="POST /ecommerce/checkout",
        description=(
            "Permits multiple percentage discount promo codes to stack multiplicatively, "
            "driving the order total negative or to $0.00."
        ),
        how_to_reproduce="Include header 'X-Simulate-Defect: DEF-EC-002' with multiple promo codes in checkout payload.",
        expected_qa_detection=(
            "QA test validates discount cap and asserts single-promo enforcement. Fails with "
            "PromoStackingViolationError when discount exceeds 50% or order total drops below minimum floor."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.PROMO_STACKING_EXPLOIT.value},
    ),
    EcommerceDefectType.PRICE_TAMPERING_INJECTION.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.PRICE_TAMPERING_INJECTION.value,
        name="Client-Side Cart Item Price Tampering",
        category="Input Validation & Security",
        affected_endpoint="POST /ecommerce/checkout",
        description=(
            "Simulates unverified trust of client-submitted item unit_price instead of recalculating "
            "authoritative prices from the product database, enabling price injection attacks (e.g. $0.01 iPhone)."
        ),
        how_to_reproduce="Send header 'X-Simulate-Defect: DEF-EC-003' with modified unit_price in cart items.",
        expected_qa_detection=(
            "QA contract test asserts server price reconciliation. Invariant fails with "
            "PriceTamperingDetectedError when client price deviates from catalog price."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.PRICE_TAMPERING_INJECTION.value},
    ),
    EcommerceDefectType.ORDER_STATE_DESYNC.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.ORDER_STATE_DESYNC.value,
        name="Order State Machine Transition Desynchronization",
        category="State Machine & Workflow",
        affected_endpoint="PUT /ecommerce/orders/{order_id}/status",
        description=(
            "Bypasses finite-state machine validation, allowing an unpaid PENDING order to transition "
            "directly to DELIVERED without payment capture or fulfillment processing."
        ),
        how_to_reproduce="Send header 'X-Simulate-Defect: DEF-EC-004' when updating order status from PENDING to DELIVERED.",
        expected_qa_detection=(
            "QA workflow test asserts valid transition sequence. Invariant fails with "
            "IllegalStateTransitionError when transition bypasses payment authorization."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.ORDER_STATE_DESYNC.value},
    ),
    EcommerceDefectType.STALE_CART_INVENTORY.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.STALE_CART_INVENTORY.value,
        name="Stale Distributed Cart Cache Inconsistency",
        category="Caching & Consistency",
        affected_endpoint="POST /ecommerce/cart/validate",
        description=(
            "Returns stale cached product availability status during cart validation even after "
            "the product was deactivated or completely deleted by warehouse inventory."
        ),
        how_to_reproduce="Send header 'X-Simulate-Defect: DEF-EC-005' during cart validation.",
        expected_qa_detection=(
            "QA integration test verifies cache invalidation. Fails with StaleCacheError when "
            "inactive product is reported as in-stock."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.STALE_CART_INVENTORY.value},
    ),
    EcommerceDefectType.REFUND_DOUBLE_CREDIT.value: EcommerceDefectDefinition(
        code=EcommerceDefectType.REFUND_DOUBLE_CREDIT.value,
        name="Concurrent Refund Double Credit Disbursement",
        category="Payment Gateway & Idempotency",
        affected_endpoint="POST /ecommerce/refunds",
        description=(
            "Lacks idempotency locking on return processing, permitting concurrent return webhooks "
            "to disburse multiple refunds for the same returned item."
        ),
        how_to_reproduce="Send header 'X-Simulate-Defect: DEF-EC-006' during duplicate refund processing.",
        expected_qa_detection=(
            "QA idempotency test asserts single disbursement per return_id. Invariant fails with "
            "DuplicateRefundDisbursedError when duplicate payout occurs."
        ),
        headers={"X-Simulate-Defect": EcommerceDefectType.REFUND_DOUBLE_CREDIT.value},
    ),
}
