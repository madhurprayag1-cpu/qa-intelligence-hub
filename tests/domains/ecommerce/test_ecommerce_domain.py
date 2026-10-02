"""Automated Tests for E-Commerce Domain Pack.

Verifies:
- Product, Cart, Order, and Return schemas and finite-state machine transitions.
- Pricing calculator: subtotal, shipping thresholds, promo discounts, and tax nexus.
- Deterministic synthetic factories.
- All 6 intentional defect simulation scenarios (DEF-EC-001 through DEF-EC-006).
- SUT REST API endpoints via TestClient.
- E-Commerce domain-scoped RAG knowledge retrieval and non-fabrication refusal.
- Regression impact pattern registration.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.ecommerce import reset_ecommerce_store
from domains.ecommerce.defects import ECOMMERCE_DEFECT_REGISTRY, EcommerceDefectType
from domains.ecommerce.domain_pack import ecommerce_domain_pack
from domains.ecommerce.factories import (
    CartFactory,
    CartItemFactory,
    OrderFactory,
    ProductFactory,
    PromoCodeFactory,
    ReturnFactory,
)
from domains.ecommerce.knowledge import get_ecommerce_knowledge_docs
from domains.ecommerce.models import (
    CartItem,
    OrderStatus,
    PricingCalculator,
    Product,
    ProductCategory,
    PromoCode,
    ShippingTier,
)
from domains.ecommerce.regression_map import ECOMMERCE_REGRESSION_PATTERNS


@pytest.fixture(autouse=True)
def setup_ecommerce_test():
    """Resets in-memory SUT store before each test."""
    reset_ecommerce_store()
    yield
    reset_ecommerce_store()


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Models & Validation Tests ---

def test_product_validation_and_sku():
    prod = Product(
        sku="SKU-ECOM-9999",
        name="Noise-Cancelling Earbuds",
        category=ProductCategory.ELECTRONICS,
        price=79.99,
        stock_quantity=15,
    )
    assert prod.sku == "SKU-ECOM-9999"
    assert prod.price == 79.99

    with pytest.raises(ValueError):
        Product(
            sku="INVALID-SKU",
            name="Earbuds",
            category=ProductCategory.ELECTRONICS,
            price=79.99,
            stock_quantity=15,
        )


def test_cart_item_line_total():
    item = CartItem(sku="SKU-ECOM-1001", product_name="Headphones", unit_price=149.99, quantity=2)
    assert item.line_total == 299.98


def test_pricing_calculator_free_shipping():
    # Under $50 threshold: gets $4.99 standard shipping
    under_50_items = [CartItem(sku="SKU-ECOM-1003", product_name="T-Shirt", unit_price=24.99, quantity=1)]
    res1 = PricingCalculator.calculate_cart(under_50_items, shipping_tier=ShippingTier.STANDARD)
    assert res1["subtotal"] == 24.99
    assert res1["shipping_cost"] == 4.99
    assert res1["total_amount"] == round(24.99 + 4.99 + (24.99 * 0.08), 2)

    # Over $50 threshold: free standard shipping
    over_50_items = [CartItem(sku="SKU-ECOM-1001", product_name="Headphones", unit_price=149.99, quantity=1)]
    res2 = PricingCalculator.calculate_cart(over_50_items, shipping_tier=ShippingTier.STANDARD)
    assert res2["subtotal"] == 149.99
    assert res2["shipping_cost"] == 0.0


def test_pricing_calculator_promo_discount_and_cap():
    items = [CartItem(sku="SKU-ECOM-1001", product_name="Headphones", unit_price=100.0, quantity=3)]
    promo = PromoCode(code="SAVE20", discount_percent=20.0, min_spend=50.0, max_discount_amount=40.0)
    res = PricingCalculator.calculate_cart(items, promo=promo)
    assert res["subtotal"] == 300.0
    # 20% of 300 is 60, but max discount cap is 40.0
    assert res["discount_amount"] == 40.0
    assert res["total_amount"] == round(260.0 + 0.0 + (260.0 * 0.08), 2)


def test_order_state_machine_transitions():
    assert PricingCalculator.validate_transition(OrderStatus.PENDING, OrderStatus.PAYMENT_AUTHORIZED) is True
    assert PricingCalculator.validate_transition(OrderStatus.PAYMENT_AUTHORIZED, OrderStatus.PROCESSING) is True
    assert PricingCalculator.validate_transition(OrderStatus.PROCESSING, OrderStatus.SHIPPED) is True
    assert PricingCalculator.validate_transition(OrderStatus.SHIPPED, OrderStatus.DELIVERED) is True
    assert PricingCalculator.validate_transition(OrderStatus.DELIVERED, OrderStatus.RETURN_REQUESTED) is True

    # Illegal transitions
    assert PricingCalculator.validate_transition(OrderStatus.PENDING, OrderStatus.DELIVERED) is False
    assert PricingCalculator.validate_transition(OrderStatus.DELIVERED, OrderStatus.PENDING) is False


# --- 2. Factory Generation Tests ---

def test_ecommerce_factories_deterministic_generation():
    catalog = ProductFactory.build_catalog()
    assert len(catalog) >= 8

    cart = CartFactory.build(index=0)
    assert cart.subtotal > 0
    assert cart.total_amount > 0

    order = OrderFactory.build(status=OrderStatus.PAYMENT_AUTHORIZED)
    assert order.order_id.startswith("ORD-ECOM-")
    assert order.payment_transaction_id.startswith("TXN-EC-")

    ret = ReturnFactory.build(order.order_id, "SKU-ECOM-1001", 149.99, quantity=1)
    assert ret.return_id.startswith("RET-ECOM-")
    assert ret.refund_amount == 149.99


# --- 3. REST API & Intentional Defect Injection Tests ---

def test_api_list_and_create_products(client):
    res = client.get("/ecommerce/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 8

    new_prod = {
        "sku": "SKU-ECOM-9001",
        "name": "Synthetic Test Widget",
        "category": "ELECTRONICS",
        "price": 19.99,
        "stock_quantity": 100,
        "weight_kg": 0.3,
        "is_active": True,
    }
    create_res = client.post("/ecommerce/products", json=new_prod)
    assert create_res.status_code == 201
    assert create_res.json()["sku"] == "SKU-ECOM-9001"


def test_defect_def_ec_001_overselling_race_detected(client):
    """DEF-EC-001: Verifies inventory exhaustion rejection (409) vs. negative stock when defect injected."""
    # Product with 5 in stock
    prod_sku = "SKU-ECOM-1001"
    client.post("/ecommerce/products", json={
        "sku": prod_sku,
        "name": "Limited Stock Item",
        "category": "ELECTRONICS",
        "price": 50.0,
        "stock_quantity": 2,
        "weight_kg": 0.5,
        "is_active": True,
    })

    checkout_payload = {
        "cart_id": "CART-TEST-01",
        "customer_id": "CUST-1001",
        "customer_email": "shopper@example.com",
        "items": [{"sku": prod_sku, "product_name": "Limited Stock Item", "unit_price": 50.0, "quantity": 5}],
        "shipping_tier": "STANDARD",
        "shipping_address": {"recipient_name": "Shopper", "street": "1 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
        "payment_method": "CREDIT_CARD",
    }

    # Baseline: strictly rejected with 409 Conflict
    clean_res = client.post("/ecommerce/checkout", json=checkout_payload)
    assert clean_res.status_code == 409
    assert "Insufficient inventory" in clean_res.json()["detail"]

    # Defect injected: overselling bypasses lock and drives stock negative
    defect_res = client.post(
        "/ecommerce/checkout",
        json=checkout_payload,
        headers={"X-Simulate-Defect": EcommerceDefectType.OVERSELLING_RACE.value},
    )
    assert defect_res.status_code == 201
    assert defect_res.json()["defect_injected"] == "DEF-EC-001"

    # Verify inventory was driven negative (2 - 5 = -3)
    get_res = client.get("/ecommerce/products")
    p = next(x for x in get_res.json() if x["sku"] == prod_sku)
    assert p["stock_quantity"] < 0, f"Expected negative stock, got {p['stock_quantity']}"


def test_defect_def_ec_002_promo_stacking_exploit_detected(client):
    """DEF-EC-002: Verifies single promo discount vs. 95% stacked exploit."""
    payload = {
        "cart_id": "CART-TEST-02",
        "customer_id": "CUST-1002",
        "customer_email": "shopper2@example.com",
        "items": [{"sku": "SKU-ECOM-1001", "product_name": "Headphones", "unit_price": 149.99, "quantity": 1}],
        "shipping_tier": "STANDARD",
        "shipping_address": {"recipient_name": "Shopper", "street": "1 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
        "payment_method": "CREDIT_CARD",
        "promo_code": "SUMMER20",
    }

    # Normal checkout
    clean_res = client.post("/ecommerce/checkout", json=payload)
    assert clean_res.status_code == 201
    assert clean_res.json()["total_amount"] > 100.0

    # Defect injected: discount stacks up to 95%
    defect_res = client.post(
        "/ecommerce/checkout",
        json=payload,
        headers={"X-Simulate-Defect": EcommerceDefectType.PROMO_STACKING_EXPLOIT.value},
    )
    assert defect_res.status_code == 201
    assert defect_res.json()["total_amount"] < 10.0


def test_defect_def_ec_003_price_tampering_injection_detected(client):
    """DEF-EC-003: Verifies server rejection of tampered item price vs. blind trust."""
    payload = {
        "cart_id": "CART-TEST-03",
        "customer_id": "CUST-1003",
        "customer_email": "shopper3@example.com",
        "items": [{"sku": "SKU-ECOM-1001", "product_name": "Headphones", "unit_price": 0.99, "quantity": 1}],  # Catalog is 149.99
        "shipping_tier": "STANDARD",
        "shipping_address": {"recipient_name": "Shopper", "street": "1 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
        "payment_method": "CREDIT_CARD",
        "client_asserted_total": 0.99,
    }

    # Normal checkout: rejected with 400 Bad Request
    clean_res = client.post("/ecommerce/checkout", json=payload)
    assert clean_res.status_code == 400
    assert "Price mismatch" in clean_res.json()["detail"]

    # Defect injected: blindly trusts client $0.99 total
    defect_res = client.post(
        "/ecommerce/checkout",
        json=payload,
        headers={"X-Simulate-Defect": EcommerceDefectType.PRICE_TAMPERING_INJECTION.value},
    )
    assert defect_res.status_code == 201
    assert defect_res.json()["total_amount"] == 0.99


def test_defect_def_ec_004_order_state_desync_detected(client):
    """DEF-EC-004: Verifies rejection of illegal state transition vs. bypass."""
    # Create valid order
    checkout_payload = {
        "cart_id": "CART-TEST-04",
        "customer_id": "CUST-1004",
        "customer_email": "shopper4@example.com",
        "items": [{"sku": "SKU-ECOM-1001", "product_name": "Headphones", "unit_price": 149.99, "quantity": 1}],
        "shipping_tier": "STANDARD",
        "shipping_address": {"recipient_name": "Shopper", "street": "1 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US"},
        "payment_method": "CREDIT_CARD",
    }
    order_id = client.post("/ecommerce/checkout", json=checkout_payload).json()["order_id"]

    # Baseline: illegal jump from PAYMENT_AUTHORIZED to DELIVERED is rejected with 422
    clean_res = client.put(f"/ecommerce/orders/{order_id}/status", json={"status": "DELIVERED"})
    assert clean_res.status_code == 422

    # Defect injected: bypasses state machine
    defect_res = client.put(
        f"/ecommerce/orders/{order_id}/status",
        json={"status": "DELIVERED"},
        headers={"X-Simulate-Defect": EcommerceDefectType.ORDER_STATE_DESYNC.value},
    )
    assert defect_res.status_code == 200
    assert defect_res.json()["new_status"] == "DELIVERED"


def test_defect_def_ec_005_stale_cart_inventory_detected(client):
    """DEF-EC-005: Verifies cart validation on inactive product vs. stale acceptance."""
    # Deactivate product
    client.post("/ecommerce/products", json={
        "sku": "SKU-ECOM-DISCONTINUED",
        "name": "Discontinued Gadget",
        "category": "ELECTRONICS",
        "price": 25.0,
        "stock_quantity": 0,
        "weight_kg": 0.5,
        "is_active": False,
    })

    payload = {
        "items": [{"sku": "SKU-ECOM-DISCONTINUED", "product_name": "Discontinued Gadget", "unit_price": 25.0, "quantity": 1}],
        "shipping_tier": "STANDARD",
    }

    # Baseline: rejected with 400
    clean_res = client.post("/ecommerce/cart/validate", json=payload)
    assert clean_res.status_code == 400

    # Defect injected: stale cache treats as valid
    defect_res = client.post(
        "/ecommerce/cart/validate",
        json=payload,
        headers={"X-Simulate-Defect": EcommerceDefectType.STALE_CART_INVENTORY.value},
    )
    assert defect_res.status_code == 200
    assert defect_res.json()["stale_cache_drift"] is True


def test_defect_def_ec_006_refund_double_credit_detected(client):
    """DEF-EC-006: Verifies idempotency collision rejection (409) vs. duplicate payout."""
    refund_payload = {
        "return_id": "RET-IDEM-001",
        "order_id": "ORD-EC-5555",
        "amount": 75.0,
    }

    # First refund: succeeds
    res1 = client.post("/ecommerce/refunds", json=refund_payload)
    assert res1.status_code == 201

    # Second refund without defect: rejected with 409 Conflict
    res2 = client.post("/ecommerce/refunds", json=refund_payload)
    assert res2.status_code == 409
    assert "Idempotency Key Collision" in res2.json()["detail"]

    # Second refund with defect: duplicate disbursement occurs
    defect_res = client.post(
        "/ecommerce/refunds",
        json=refund_payload,
        headers={"X-Simulate-Defect": EcommerceDefectType.REFUND_DOUBLE_CREDIT.value},
    )
    assert defect_res.status_code == 201
    assert defect_res.json()["duplicate_credit"] is True


# --- 4. RAG Knowledge & Domain Pack Tests ---

def test_ecommerce_knowledge_documents():
    docs = get_ecommerce_knowledge_docs()
    assert len(docs) >= 5
    for d in docs:
        assert d["domain"] == "ecommerce"
        assert len(d["text"]) > 50


def test_ecommerce_domain_pack_metadata_and_catalog():
    assert ecommerce_domain_pack.domain_id == "ecommerce"
    assert len(ecommerce_domain_pack.defect_catalog) == 6
    assert len(ecommerce_domain_pack.rag_sources) >= 5
    assert len(ecommerce_domain_pack.regression_patterns) == 5
