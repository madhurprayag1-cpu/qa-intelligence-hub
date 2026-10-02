"""E-Commerce Domain Pack for QA Intelligence Hub.

Provides models, deterministic synthetic data factories, RAG knowledge corpus,
intentional defect engineering catalog, and regression impact patterns for
enterprise e-commerce platforms (Product catalog, Cart, Checkout, Concurrency, Orders, Refunds).
"""

from domains.ecommerce.domain_pack import ecommerce_domain_pack

__all__ = ["ecommerce_domain_pack"]
