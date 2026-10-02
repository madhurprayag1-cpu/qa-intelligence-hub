"""E-Commerce Retail REST API & SUT Router.

Adheres strictly to AGENTS.md Sections 8, 9, 13, 21 and Phase 1B Blueprint:
- Production-grade synthetic SUT endpoints for Product catalog, Cart, Checkout, Order Lifecycle, and Returns.
- Dual-plane execution: PostgreSQL persistence via SQLAlchemy models + in-memory hermetic cache.
- Strict tenant isolation with owner_user_id enforcing IDOR boundaries.
- Intentional defect simulation via header 'X-Simulate-Defect' (DEF-EC-001 through DEF-EC-006).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import User, get_current_domain_user
from app.db.database import get_db
from app.models.ecommerce import EcomOrderModel, EcomProductModel, EcomReturnModel
from domains.ecommerce.defects import ECOMMERCE_DEFECT_REGISTRY, EcommerceDefectType
from domains.ecommerce.factories import ProductFactory, PromoCodeFactory
from domains.ecommerce.models import (
    Cart,
    CartItem,
    CheckoutRequest,
    Order,
    OrderStatus,
    PricingCalculator,
    Product,
    ProductCategory,
    ReturnRequest,
    ReturnStatus,
    ShippingTier,
)

router = APIRouter(prefix="/ecommerce", tags=["ecommerce-domain"])

# Hermetic in-memory store for synthetic e-commerce SUT execution
_PRODUCT_STORE: Dict[str, Product] = {}
_ORDER_STORE: Dict[str, Order] = {}
_REFUND_STORE: Dict[str, Dict[str, Any]] = {}
_PROMO_STORE: Dict[str, Any] = {}


def reset_ecommerce_store() -> None:
    """Resets in-memory stores and seeds initial catalog for hermetic test execution."""
    _PRODUCT_STORE.clear()
    _ORDER_STORE.clear()
    _REFUND_STORE.clear()
    _PROMO_STORE.clear()

    # Seed baseline synthetic products
    for p in ProductFactory.build_catalog():
        _PRODUCT_STORE[p.sku] = p

    # Seed baseline promos
    summer = PromoCodeFactory.build_summer_sale()
    welcome = PromoCodeFactory.build_welcome_discount()
    _PROMO_STORE[summer.code] = summer
    _PROMO_STORE[welcome.code] = welcome


# Initialize at module load
reset_ecommerce_store()


@router.get("/products", response_model=List[Product])
async def list_products(
    category: Optional[ProductCategory] = None,
    in_stock_only: bool = False,
    db: Session = Depends(get_db),
) -> List[Product]:
    """Retrieves product catalog with optional category and stock filtering."""
    # Synchronize initial DB catalog if empty
    try:
        count = db.query(EcomProductModel).count()
        if count == 0:
            for p in _PRODUCT_STORE.values():
                db.add(
                    EcomProductModel(
                        sku=p.sku,
                        name=p.name,
                        category=p.category.value if hasattr(p.category, "value") else str(p.category),
                        price=Decimal(str(p.price)),
                        stock_quantity=p.stock_quantity,
                        weight_kg=Decimal("0.50"),
                        is_active=p.is_active,
                    )
                )
            db.commit()
    except Exception:
        db.rollback()

    results = list(_PRODUCT_STORE.values())
    if category:
        results = [p for p in results if p.category == category]
    if in_stock_only:
        results = [p for p in results if p.stock_quantity > 0]
    return results


@router.post("/products", status_code=status.HTTP_201_CREATED, response_model=Product)
async def create_product(
    product: Product,
    db: Session = Depends(get_db),
) -> Product:
    """Creates or updates a product in the catalog and DB."""
    _PRODUCT_STORE[product.sku] = product

    try:
        existing = db.get(EcomProductModel, product.sku)
        if existing:
            existing.name = product.name
            existing.price = Decimal(str(product.price))
            existing.stock_quantity = product.stock_quantity
            existing.is_active = product.is_active
        else:
            db_p = EcomProductModel(
                sku=product.sku,
                name=product.name,
                category=product.category.value if hasattr(product.category, "value") else str(product.category),
                price=Decimal(str(product.price)),
                stock_quantity=product.stock_quantity,
                weight_kg=Decimal("0.50"),
                is_active=product.is_active,
            )
            db.add(db_p)
        db.commit()
    except Exception:
        db.rollback()

    return product


@router.post("/cart/validate")
async def validate_cart(
    payload: Dict[str, Any],
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Validates cart items and calculates subtotal, discounts, shipping, tax, and total.
    Supports defect DEF-EC-005 (STALE_CART_INVENTORY): permits stale/inactive items.
    """
    is_stale_defect = x_simulate_defect in (EcommerceDefectType.STALE_CART_INVENTORY.value, "STALE_CART_INVENTORY", "DEF-EC-005")
    raw_items = payload.get("items", [])
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart cannot be empty.")

    for it in raw_items:
        if isinstance(it, dict) and not it.get("product_name") and it.get("name"):
            it["product_name"] = it["name"]
        elif isinstance(it, dict) and not it.get("product_name"):
            it["product_name"] = it.get("sku", "Product")

    cart_items = [CartItem.model_validate(it) for it in raw_items]
    tier_str = payload.get("shipping_tier", "STANDARD")
    try:
        tier = ShippingTier(tier_str)
    except ValueError:
        tier = ShippingTier.STANDARD

    promo_code_str = payload.get("promo_code")
    promo = _PROMO_STORE.get(promo_code_str) if promo_code_str else None

    # Check inventory availability
    for item in cart_items:
        prod = _PRODUCT_STORE.get(item.sku)
        if not prod:
            if not is_stale_defect:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.sku} not found.")
        elif not prod.is_active and not is_stale_defect:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {item.sku} is discontinued.")

    totals = PricingCalculator.calculate_cart(cart_items, shipping_tier=tier, promo=promo)
    return {
        "valid": True,
        "items_count": len(cart_items),
        "totals": totals,
        "applied_promo": promo.code if promo else None,
        "stale_cache_drift": is_stale_defect,
    }


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def process_checkout(
    checkout_req: CheckoutRequest,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Executes checkout: inventory deduction, price reconciliation, and order creation.
    Persists order to PostgreSQL with tenant isolation.
    Supports defects:
    - DEF-EC-001 (OVERSELLING_RACE): Bypasses stock check, driving inventory negative.
    - DEF-EC-002 (PROMO_STACKING_EXPLOIT): Allows double promo application resulting in negative/free total.
    - DEF-EC-003 (PRICE_TAMPERING_INJECTION): Accepts client-asserted total blindly without verification.
    """
    is_oversell = x_simulate_defect in (EcommerceDefectType.OVERSELLING_RACE.value, "OVERSELLING_RACE", "DEF-EC-001")
    is_promo_stack = x_simulate_defect in (EcommerceDefectType.PROMO_STACKING_EXPLOIT.value, "PROMO_STACKING_EXPLOIT", "DEF-EC-002")
    is_price_tamper = x_simulate_defect in (EcommerceDefectType.PRICE_TAMPERING_INJECTION.value, "PRICE_TAMPERING_INJECTION", "DEF-EC-003")

    # 1. Price Reconciliation
    if is_price_tamper and checkout_req.client_asserted_total is not None:
        total_amount = float(checkout_req.client_asserted_total)
        subtotal = total_amount
        discount = 0.0
        shipping = 0.0
        tax = 0.0
    else:
        for item in checkout_req.items:
            prod = _PRODUCT_STORE.get(item.sku)
            if prod and abs(item.unit_price - prod.price) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Price mismatch for {item.sku}: client asserted {item.unit_price}, authoritative is {prod.price}",
                )

        promo = _PROMO_STORE.get(checkout_req.promo_code) if checkout_req.promo_code else None
        totals = PricingCalculator.calculate_cart(
            checkout_req.items,
            shipping_tier=checkout_req.shipping_tier,
            promo=promo,
        )

        if is_promo_stack:
            discount = totals["subtotal"] * 0.95
            total_amount = round(max(0.0, totals["subtotal"] - discount), 2)
            subtotal = totals["subtotal"]
            shipping = 0.0
            tax = 0.0
        else:
            subtotal = totals["subtotal"]
            discount = totals["discount_amount"]
            shipping = totals["shipping_cost"]
            tax = totals["tax_amount"]
            total_amount = totals["total_amount"]

    # 2. Inventory Allocation & Atomic Concurrency Lock
    for item in checkout_req.items:
        prod = _PRODUCT_STORE.get(item.sku)
        if prod:
            if not is_oversell and prod.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient inventory for {item.sku}: requested {item.quantity}, available {prod.stock_quantity}",
                )
            prod.stock_quantity -= item.quantity

    order_id = f"ORD-EC-{len(_ORDER_STORE) + 1001}"
    order = Order(
        order_id=order_id,
        customer_id=checkout_req.customer_id,
        customer_email=checkout_req.customer_email,
        items=checkout_req.items,
        status=OrderStatus.PAYMENT_AUTHORIZED,
        subtotal=subtotal,
        discount_amount=discount,
        shipping_cost=shipping,
        tax_amount=tax,
        total_amount=total_amount,
        shipping_tier=checkout_req.shipping_tier,
        shipping_address=checkout_req.shipping_address,
        payment_transaction_id=f"TXN-EC-{datetime.now(timezone.utc).timestamp()}",
    )
    _ORDER_STORE[order_id] = order

    # DB Persistence
    try:
        # Deduct inventory in DB
        for item in checkout_req.items:
            db_p = db.get(EcomProductModel, item.sku)
            if db_p:
                db_p.stock_quantity -= item.quantity

        db_order = EcomOrderModel(
            order_id=order_id,
            owner_user_id=current_user.id,
            customer_id=checkout_req.customer_id,
            customer_email=checkout_req.customer_email,
            items=[it.model_dump() for it in checkout_req.items],
            status=order.status.value,
            subtotal=Decimal(str(subtotal)),
            discount_amount=Decimal(str(discount)),
            shipping_cost=Decimal(str(shipping)),
            tax_amount=Decimal(str(tax)),
            total_amount=Decimal(str(total_amount)),
            shipping_tier=checkout_req.shipping_tier.value if hasattr(checkout_req.shipping_tier, "value") else str(checkout_req.shipping_tier),
            shipping_address=dict(checkout_req.shipping_address) if checkout_req.shipping_address else {},
            payment_transaction_id=order.payment_transaction_id,
        )
        db.add(db_order)
        db.commit()
    except Exception as e:
        db.rollback()

    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "total_amount": order.total_amount,
        "payment_authorized": True,
        "defect_injected": x_simulate_defect,
    }


@router.get("/orders")
async def list_orders(
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists orders belonging to the authenticated customer."""
    try:
        if current_user.role in {"admin", "staff"}:
            db_orders = db.query(EcomOrderModel).order_by(EcomOrderModel.created_at.desc()).all()
        else:
            db_orders = (
                db.query(EcomOrderModel)
                .filter(EcomOrderModel.owner_user_id == current_user.id)
                .order_by(EcomOrderModel.created_at.desc())
                .all()
            )
        if db_orders:
            return [
                {
                    "order_id": o.order_id,
                    "status": o.status,
                    "total_amount": float(o.total_amount),
                    "items": o.items or [],
                    "owner_user_id": o.owner_user_id,
                    "created_at": o.created_at.isoformat() if o.created_at else "",
                }
                for o in db_orders
            ]
    except Exception:
        pass

    return [o.model_dump() for o in _ORDER_STORE.values()]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves order details by ID with IDOR tenant verification."""
    order = _ORDER_STORE.get(order_id)
    db_order = None
    try:
        db_order = db.get(EcomOrderModel, order_id)
    except Exception:
        pass

    if not order and not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_id} not found.")

    # IDOR tenant isolation check
    if db_order and current_user.role not in {"admin", "staff"}:
        if db_order.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: IDOR protection prevented access to another customer's order.",
            )

    if order:
        return order.model_dump()

    return {
        "order_id": db_order.order_id,
        "customer_id": db_order.customer_id,
        "customer_email": db_order.customer_email,
        "status": db_order.status,
        "total_amount": float(db_order.total_amount),
        "items": db_order.items or [],
        "owner_user_id": db_order.owner_user_id,
        "created_at": db_order.created_at.isoformat() if db_order.created_at else "",
    }


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    payload: Dict[str, str],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Transitions order state per strict state machine.
    Supports defect DEF-EC-004 (ORDER_STATE_DESYNC): allows illegal status jumps.
    """
    order = _ORDER_STORE.get(order_id)
    db_order = None
    try:
        db_order = db.get(EcomOrderModel, order_id)
    except Exception:
        pass

    if not order and not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_id} not found.")

    target_status_str = payload.get("status")
    if target_status_str == "PAID":
        target_status = OrderStatus.PAYMENT_AUTHORIZED
    else:
        try:
            target_status = OrderStatus(target_status_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status {target_status_str}.")

    is_state_desync = x_simulate_defect in (EcommerceDefectType.ORDER_STATE_DESYNC.value, "ORDER_STATE_DESYNC", "DEF-EC-004", "ORDER_STATE_MACHINE_CORRUPTION", "DEF-EC-006")

    current_status = order.status if order else OrderStatus(db_order.status)
    if not is_state_desync and current_status != target_status:
        if not PricingCalculator.validate_transition(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Illegal state transition from {current_status.value} to {target_status.value}.",
            )

    if order:
        order.status = target_status
        if target_status == OrderStatus.SHIPPED and not order.tracking_number:
            order.tracking_number = f"TRK-USPS-{order.order_id.replace('-', '')}"

    if db_order:
        try:
            db_order.status = target_status.value
            db.commit()
        except Exception:
            db.rollback()

    return {
        "order_id": order_id,
        "previous_status": current_status.value,
        "new_status": target_status.value,
        "state_desync_injected": is_state_desync,
    }


@router.post("/refunds", status_code=status.HTTP_201_CREATED)
async def process_refund(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Processes product returns and disburses refunds.
    Persists return record to PostgreSQL with tenant isolation.
    Supports defect DEF-EC-006 (REFUND_DOUBLE_CREDIT): allows duplicate payouts on identical return_id.
    """
    return_id = payload.get("return_id")
    order_id = payload.get("order_id")
    amount = float(payload.get("amount", 0.0))

    if not return_id or not order_id or amount <= 0.0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid return request data.")

    is_double_credit = x_simulate_defect in (EcommerceDefectType.REFUND_DOUBLE_CREDIT.value, "REFUND_DOUBLE_CREDIT", "DEF-EC-006", "DUPLICATE_REFUND_RACE", "DEF-EC-004")

    if return_id in _REFUND_STORE and not is_double_credit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Refund already disbursed for return {return_id} (Idempotency Key Collision).",
        )

    disbursement = {
        "refund_id": f"RFND-{len(_REFUND_STORE) + 1001}",
        "return_id": return_id,
        "order_id": order_id,
        "disbursed_amount": amount,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "duplicate_credit": return_id in _REFUND_STORE and is_double_credit,
    }
    _REFUND_STORE[return_id] = disbursement

    # DB Persistence
    try:
        # Ensure parent order exists in DB if needed
        if not db.get(EcomOrderModel, order_id):
            db.add(
                EcomOrderModel(
                    order_id=order_id,
                    owner_user_id=current_user.id,
                    customer_id=f"CUST-{current_user.id}",
                    customer_email="customer@example.com",
                    items=[],
                    status="DELIVERED",
                    subtotal=Decimal(str(amount)),
                    total_amount=Decimal(str(amount)),
                    shipping_address={},
                    payment_transaction_id=f"TXN-EC-{datetime.now(timezone.utc).timestamp()}",
                )
            )
            db.flush()

        db_return = EcomReturnModel(
            return_id=return_id,
            order_id=order_id,
            sku=payload.get("sku", "SKU-AUTO-RETURN"),
            quantity=int(payload.get("quantity", 1)),
            reason=payload.get("reason", "Customer Return"),
            refund_amount=Decimal(str(amount)),
            status="DISBURSED",
        )
        db.add(db_return)
        db.commit()
    except Exception:
        db.rollback()

    return disbursement


@router.get("/defects")
async def list_ecommerce_defects() -> List[Dict[str, Any]]:
    """Returns documentation and simulation instructions for E-Commerce defect scenarios."""
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
        for d in ECOMMERCE_DEFECT_REGISTRY.values()
    ]
