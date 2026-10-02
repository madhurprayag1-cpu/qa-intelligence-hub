"""E-Commerce Domain Knowledge Corpus for Scalable RAG.

Adheres strictly to AGENTS.md Section 10 & 18:
- Domain-isolated knowledge documents tagged with domain='ecommerce'.
- Authoritative reference policies for Returns, Shipping SLAs, Promos, Inventory Locks, and Tax Nexus.
"""

from typing import Any, Dict, List


def get_ecommerce_knowledge_docs() -> List[Dict[str, Any]]:
    """Returns curated synthetic knowledge documents for e-commerce domain-scoped RAG."""
    return [
        {
            "document_id": "ECOMMERCE-RETURNS-01",
            "domain": "ecommerce",
            "text": (
                "Standard E-Commerce Return & Refund Policy: Customers may initiate a return within 30 calendar days "
                "of order delivery. All returned merchandise must be unused, in original packaging, and with tags attached. "
                "Intimate apparel, opened beauty products, and downloadable software licenses are strictly non-returnable. "
                "Upon warehouse physical inspection and RMA approval, automated refunds are disbursed to the original "
                "payment method within 3 to 5 business days. A standard $5.00 restocking fee applies to oversized electronics."
            ),
            "metadata": {
                "category": "Customer Support & Returns",
                "standard": "Consumer Rights Directive / FTC Regulations",
                "source": "returns_refund_policy.md",
            },
        },
        {
            "document_id": "ECOMMERCE-SHIPPING-01",
            "domain": "ecommerce",
            "text": (
                "Order Fulfillment & Shipping SLA Guidelines: The platform offers four shipping tiers. "
                "Standard Shipping ($4.99 flat rate) fulfills in 3 to 5 business days and is complimentary on all orders "
                "with a post-discount merchandise subtotal exceeding $50.00. Expedited Shipping ($12.99) delivers within "
                "2 business days via FedEx/UPS Express. Overnight Delivery ($24.99) provides guaranteed next-business-day delivery "
                "for orders placed before 2:00 PM EST. Hazardous lithium-ion batteries cannot be shipped via air express."
            ),
            "metadata": {
                "category": "Logistics & Fulfillment",
                "standard": "USPS / FedEx Domestic Shipping SLA",
                "source": "shipping_fulfillment_sla.md",
            },
        },
        {
            "document_id": "ECOMMERCE-PROMO-RULES-01",
            "domain": "ecommerce",
            "text": (
                "Promotional Discount & Coupon Enforcement Rules: Only one promotional discount code may be applied per checkout cart. "
                "Stacking multiple percentage-off or dollar-off coupons is strictly blocked by the checkout validation engine. "
                "Maximum allowable promotional discount is capped at 50% of the cart subtotal or $100.00, whichever is lower. "
                "Promotions with minimum spend thresholds (e.g. SUMMER20 requiring $50.00) evaluate against the pre-tax, "
                "pre-shipping subtotal. Gift cards, clearance items, and manufacturer-excluded brands do not qualify for promotional discounts."
            ),
            "metadata": {
                "category": "Pricing & Promotions",
                "standard": "E-Commerce Financial Reconciliation",
                "source": "promotional_discount_rules.md",
            },
        },
        {
            "document_id": "ECOMMERCE-INVENTORY-SLA-01",
            "domain": "ecommerce",
            "text": (
                "High-Concurrency Flash Sale & Inventory Reservation Protocol: High-demand product launches mandate atomic "
                "distributed inventory reservation locks (row-level database locking). When a shopper proceeds to checkout, "
                "stock is placed on temporary hold for exactly 15 minutes. If checkout is not completed within the timeout window, "
                "the reserved inventory count is automatically released back to the available pool. The inventory ledger strictly "
                "prohibits negative stock levels, and overselling triggers an immediate transaction abort with HTTP 409 Conflict."
            ),
            "metadata": {
                "category": "Inventory Management & Concurrency",
                "standard": "Distributed Transaction ACID Invariants",
                "source": "inventory_reservation_sla.md",
            },
        },
        {
            "document_id": "ECOMMERCE-TAX-NEXUS-01",
            "domain": "ecommerce",
            "text": (
                "Sales Tax Nexus & Jurisdictional Compliance: Sales tax is calculated dynamically using destination-based sourcing "
                "rules in compliance with the South Dakota v. Wayfair Supreme Court precedent. The platform maintains automatic tax nexus "
                "evaluation across all 50 US states, charging state and municipal sales tax based on the delivery postal code. "
                "Standard taxable goods default to an 8.0% baseline rate when third-party geolocation rate lookups are in fallback mode. "
                "Groceries and prescription health products are configured as tax-exempt across qualifying jurisdictions."
            ),
            "metadata": {
                "category": "Taxation & Legal Compliance",
                "standard": "Streamlined Sales Tax Agreement (SSUTA)",
                "source": "sales_tax_nexus_compliance.md",
            },
        },
    ]
