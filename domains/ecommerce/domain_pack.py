"""E-Commerce Domain Pack Definition & Registration.

Adheres strictly to Master Architecture Directive & AGENTS.md Sections 1-4:
- Implements DomainPack protocol for E-Commerce / Digital Retail Systems.
- Auto-registers with the central domain_registry.
- Encapsulates domain capabilities, RAG sources, defect catalog, regression patterns, and metadata.
"""

from domain_registry import DomainCapability, DomainPack, domain_registry
from domains.ecommerce.defects import ECOMMERCE_DEFECT_REGISTRY
from domains.ecommerce.knowledge import get_ecommerce_knowledge_docs
from domains.ecommerce.regression_map import ECOMMERCE_REGRESSION_PATTERNS


def get_ecommerce_factories():
    from domains.ecommerce.factories import (
        CartFactory,
        CartItemFactory,
        OrderFactory,
        ProductFactory,
        PromoCodeFactory,
        ReturnFactory,
    )
    from domains.ecommerce.models import PricingCalculator
    return {
        "ProductFactory": ProductFactory,
        "CartItemFactory": CartItemFactory,
        "CartFactory": CartFactory,
        "OrderFactory": OrderFactory,
        "ReturnFactory": ReturnFactory,
        "PromoCodeFactory": PromoCodeFactory,
        "PricingCalculator": PricingCalculator,
    }


ecommerce_domain_pack = DomainPack(
    domain_id="ecommerce",
    name="E-Commerce & Digital Retail Systems",
    version="1.0.0",
    description="Product catalog, shopping cart, promo code discounting, flash-sale inventory reservation, order state machine, and automated returns.",
    capabilities=[
        DomainCapability.API_TESTING,
        DomainCapability.DATABASE_TESTING,
        DomainCapability.CONTRACT_TESTING,
        DomainCapability.RAG_AI,
        DomainCapability.AGENTIC_QA,
        DomainCapability.SECURITY_AUDIT,
        DomainCapability.PERFORMANCE_BENCHMARK,
        DomainCapability.QUALITY_GATE,
        DomainCapability.DEFECT_INJECTION,
    ],
    rag_sources=[
        "ECOMMERCE-RETURNS-01",
        "ECOMMERCE-SHIPPING-01",
        "ECOMMERCE-PROMO-RULES-01",
        "ECOMMERCE-INVENTORY-SLA-01",
        "ECOMMERCE-TAX-NEXUS-01",
    ],
    factories_provider=get_ecommerce_factories,
    rag_docs_provider=get_ecommerce_knowledge_docs,
    defect_catalog={
        d.code: f"{d.name}: {d.description}"
        for d in ECOMMERCE_DEFECT_REGISTRY.values()
    },
    regression_patterns=ECOMMERCE_REGRESSION_PATTERNS,
    metadata={
        "regulatory_standard": "FTC Mail Order Rule / Consumer Rights Directive / PCI DSS",
        "primary_currency": "USD",
        "supported_categories": ["ELECTRONICS", "APPAREL", "HOME_GOODS", "BOOKS", "BEAUTY"],
    },
)

# Auto-register with central registry
domain_registry.register(ecommerce_domain_pack)
