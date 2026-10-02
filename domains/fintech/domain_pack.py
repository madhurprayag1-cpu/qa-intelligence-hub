"""FinTech Domain Pack Definition & Registration.

Adheres strictly to the Master Architecture Directive & AGENTS.md Sections 1-4:
- Implements DomainPack protocol for FinTech / Digital Banking & Ledger Systems.
- Auto-registers with the central domain_registry.
- Encapsulates domain capabilities, RAG sources, defect catalog, regression patterns, and metadata.
"""

from domain_registry import DomainCapability, DomainPack, domain_registry
from domains.fintech.defects import FINTECH_DEFECT_REGISTRY
from domains.fintech.knowledge import get_fintech_knowledge_docs
from domains.fintech.regression_map import FINTECH_REGRESSION_PATTERNS


def get_fintech_factories():
    from domains.fintech.factories import (
        AccountFactory,
        TransferFactory,
        KYCFactory,
        FraudAnomalyFactory,
        FXCalculator,
    )
    return {
        "AccountFactory": AccountFactory,
        "TransferFactory": TransferFactory,
        "KYCFactory": KYCFactory,
        "FraudAnomalyFactory": FraudAnomalyFactory,
        "FXCalculator": FXCalculator,
    }


fintech_domain_pack = DomainPack(
    domain_id="fintech",
    name="FinTech / Digital Banking & Ledger Systems",
    version="1.0.0",
    description="Double-entry bookkeeping, SWIFT ISO 20022 messaging, KYC/AML compliance tiers, transaction velocity fraud detection, and foreign exchange currency precision.",
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
        "FINTECH-LEDGER-01",
        "FINTECH-ISO20022-01",
        "FINTECH-KYC-AML-01",
        "FINTECH-FRAUD-01",
        "FINTECH-PCIDSS-01",
    ],
    factories_provider=get_fintech_factories,
    rag_docs_provider=get_fintech_knowledge_docs,
    defect_catalog={
        d.code: f"{d.name}: {d.description}"
        for d in FINTECH_DEFECT_REGISTRY.values()
    },
    regression_patterns=FINTECH_REGRESSION_PATTERNS,
    metadata={
        "iso_standard": "ISO 20022:2022 (pain.001 / pacs.008 / camt.053)",
        "regulatory_frameworks": ["PCI DSS 4.0", "Bank Secrecy Act / AML", "Basel III"],
        "supported_currencies": ["USD", "EUR", "GBP", "CHF", "JPY"],
        "aml_reporting_threshold": 10000.0,
        "max_velocity_threshold_per_minute": 3,
    },
)

# Auto-register with central platform registry
domain_registry.register(fintech_domain_pack)
