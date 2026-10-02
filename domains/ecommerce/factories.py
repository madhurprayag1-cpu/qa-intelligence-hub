"""Synthetic Data Factories for E-Commerce Domain.

Adheres strictly to AGENTS.md Section 12 & Master Architecture Directive:
- 100% synthetic, deterministic data generation inheriting from base_factories.
- Zero proprietary employer or customer data.
- Covers Products, Customers, Carts, Orders, Returns, and Promo Codes.
"""

from typing import Any, Dict, List, Optional
from base_factories import IdentifierGenerator, PersonGenerator, SecurityPayloadGenerator
from domains.ecommerce.models import (
    Cart,
    CartItem,
    Order,
    OrderStatus,
    PricingCalculator,
    Product,
    ProductCategory,
    PromoCode,
    ReturnRequest,
    ReturnStatus,
    ShippingTier,
)


class ProductFactory:
    """Deterministic synthetic product catalog factory."""

    SAMPLE_CATALOG = [
        ("SKU-ECOM-1001", "Wireless Noise-Cancelling Headphones", ProductCategory.ELECTRONICS, 149.99, 50, 0.4),
        ("SKU-ECOM-1002", "Mechanical Gaming Keyboard RGB", ProductCategory.ELECTRONICS, 89.50, 35, 1.1),
        ("SKU-ECOM-1003", "Organic Cotton Casual T-Shirt", ProductCategory.APPAREL, 24.99, 120, 0.2),
        ("SKU-ECOM-1004", "Waterproof Trail Running Shoes", ProductCategory.APPAREL, 119.00, 40, 0.8),
        ("SKU-ECOM-1005", "Ceramic Pour-Over Coffee Maker", ProductCategory.HOME_GOODS, 34.50, 60, 0.7),
        ("SKU-ECOM-1006", "Smart LED Desk Lamp with Dimmer", ProductCategory.HOME_GOODS, 45.00, 75, 1.2),
        ("SKU-ECOM-1007", "Designing Data-Intensive Applications", ProductCategory.BOOKS, 42.00, 90, 0.9),
        ("SKU-ECOM-1008", "Hydrating Hyaluronic Acid Facial Serum", ProductCategory.BEAUTY, 28.00, 85, 0.15),
    ]

    @classmethod
    def build(cls, index: int = 0, stock: Optional[int] = None) -> Product:
        template = cls.SAMPLE_CATALOG[index % len(cls.SAMPLE_CATALOG)]
        return Product(
            sku=template[0],
            name=template[1],
            category=template[2],
            price=template[3],
            stock_quantity=stock if stock is not None else template[4],
            weight_kg=template[5],
            is_active=True,
        )

    @classmethod
    def build_catalog(cls) -> List[Product]:
        return [cls.build(i) for i in range(len(cls.SAMPLE_CATALOG))]


class CartItemFactory:
    """Builds synthetic cart items."""

    @classmethod
    def build(cls, product_index: int = 0, quantity: int = 1) -> CartItem:
        prod = ProductFactory.build(product_index)
        return CartItem(
            sku=prod.sku,
            product_name=prod.name,
            unit_price=prod.price,
            quantity=quantity,
        )


class PromoCodeFactory:
    """Builds valid and test promo codes."""

    @classmethod
    def build_summer_sale(cls) -> PromoCode:
        return PromoCode(
            code="SUMMER20",
            discount_percent=20.0,
            min_spend=50.0,
            max_discount_amount=40.0,
            is_active=True,
        )

    @classmethod
    def build_welcome_discount(cls) -> PromoCode:
        return PromoCode(
            code="WELCOME10",
            discount_percent=10.0,
            min_spend=0.0,
            max_discount_amount=20.0,
            is_active=True,
        )


class CartFactory:
    """Builds synthetic shopping carts with calculated totals."""

    @classmethod
    def build(
        cls,
        index: int = 0,
        item_count: int = 2,
        shipping_tier: ShippingTier = ShippingTier.STANDARD,
        promo: Optional[PromoCode] = None,
    ) -> Cart:
        items = [CartItemFactory.build(i, quantity=1) for i in range(item_count)]
        calc = PricingCalculator.calculate_cart(items, shipping_tier=shipping_tier, promo=promo)
        return Cart(
            cart_id=f"CART-{IdentifierGenerator.generate_alphanumeric(8)}",
            customer_id=f"CUST-{IdentifierGenerator.generate_numeric(6)}",
            items=items,
            shipping_tier=shipping_tier,
            applied_promo=promo,
            subtotal=calc["subtotal"],
            discount_amount=calc["discount_amount"],
            shipping_cost=calc["shipping_cost"],
            tax_amount=calc["tax_amount"],
            total_amount=calc["total_amount"],
        )


class OrderFactory:
    """Builds realistic synthetic e-commerce orders."""

    @classmethod
    def build(
        cls,
        status: OrderStatus = OrderStatus.PENDING,
        shipping_tier: ShippingTier = ShippingTier.STANDARD,
        index: int = 0,
    ) -> Order:
        person = PersonGenerator.generate(index=index)
        cart = CartFactory.build(index=index, shipping_tier=shipping_tier)
        order_ref = f"ORD-ECOM-{IdentifierGenerator.generate_numeric(8)}"
        return Order(
            order_id=order_ref,
            customer_id=cart.customer_id,
            customer_email=person.email,
            items=cart.items,
            status=status,
            subtotal=cart.subtotal,
            discount_amount=cart.discount_amount,
            shipping_cost=cart.shipping_cost,
            tax_amount=cart.tax_amount,
            total_amount=cart.total_amount,
            shipping_tier=shipping_tier,
            shipping_address={
                "recipient_name": person.full_name,
                "street": f"{100 + index} Market Street",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country": "US",
            },
            payment_transaction_id=f"TXN-EC-{IdentifierGenerator.generate_alphanumeric(10)}",
            tracking_number=f"TRK-USPS-{IdentifierGenerator.generate_numeric(12)}" if status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED] else None,
        )


class ReturnFactory:
    """Builds synthetic return requests."""

    @classmethod
    def build(cls, order_id: str, sku: str, unit_price: float, quantity: int = 1) -> ReturnRequest:
        refund_total = round(unit_price * quantity, 2)
        return ReturnRequest(
            return_id=f"RET-ECOM-{IdentifierGenerator.generate_numeric(8)}",
            order_id=order_id,
            sku=sku,
            quantity=quantity,
            reason="Item did not match description",
            status=ReturnStatus.REQUESTED,
            refund_amount=refund_total,
            restocking_fee=0.0,
        )
