"""Regression Test Impact Mapping for E-Commerce Domain.

Adheres to AGENTS.md Section 5 & Master Architecture Directive:
- Maps changed files or PR diff tokens to targeted e-commerce test suites.
- Plugs dynamically into qa-engine/regression_selector.py without core modifications.
"""

from typing import Any, Dict, List

ECOMMERCE_REGRESSION_PATTERNS: Dict[str, Dict[str, Any]] = {
    "ecommerce_catalog": {
        "patterns": ["ecommerce", "catalog", "product", "sku", "category"],
        "tests": [
            "tests/domains/ecommerce/test_ecommerce_domain.py",
        ],
        "tags": ["ecommerce", "catalog", "product"],
        "ui_specs": [],
    },
    "ecommerce_cart_pricing": {
        "patterns": ["cart", "promo", "coupon", "discount", "pricing", "shipping"],
        "tests": [
            "tests/domains/ecommerce/test_ecommerce_domain.py",
        ],
        "tags": ["ecommerce", "cart", "pricing", "promo"],
        "ui_specs": [],
    },
    "ecommerce_checkout_inventory": {
        "patterns": ["checkout", "oversell", "inventory", "stock", "hold"],
        "tests": [
            "tests/domains/ecommerce/test_ecommerce_domain.py",
        ],
        "tags": ["ecommerce", "checkout", "inventory", "concurrency"],
        "ui_specs": [],
    },
    "ecommerce_order_lifecycle": {
        "patterns": ["order", "fulfillment", "tracking", "status", "transition"],
        "tests": [
            "tests/domains/ecommerce/test_ecommerce_domain.py",
        ],
        "tags": ["ecommerce", "order", "state_machine"],
        "ui_specs": [],
    },
    "ecommerce_returns_refunds": {
        "patterns": ["return", "refund", "rma", "restock", "credit"],
        "tests": [
            "tests/domains/ecommerce/test_ecommerce_domain.py",
        ],
        "tags": ["ecommerce", "returns", "refunds", "idempotency"],
        "ui_specs": [],
    },
}
