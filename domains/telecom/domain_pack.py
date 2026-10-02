"""Telecom Domain Pack Definition & Registration.

Adheres strictly to Master Architecture Directive & AGENTS.md Sections 1-4:
- Implements DomainPack protocol for Telecommunications / 5G Mobile & BSS/OSS.
- Auto-registers with the central domain_registry.
- Encapsulates domain capabilities, RAG sources, defect catalog, regression patterns, and metadata.
"""

from domain_registry import DomainCapability, DomainPack, domain_registry
from domains.telecom.defects import TELECOM_DEFECT_REGISTRY
from domains.telecom.factories import get_telecom_factories
from domains.telecom.knowledge import get_telecom_rag_docs
from domains.telecom.regression_map import TELECOM_REGRESSION_MAP


telecom_domain_pack = DomainPack(
    domain_id="telecom",
    name="Telecom / 5G Mobile & BSS/OSS",
    version="1.0.0",
    description="Subscriber provisioning, SIM/eSIM lifecycle, tariff plan rating, real-time CDR billing, FUP data throttling, and international roaming governance.",
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
        "TELECOM-FUP-01",
        "TELECOM-ROAMING-01",
        "TELECOM-BILLING-01",
        "TELECOM-PORTABILITY-01",
        "TELECOM-CDR-SLA-01",
    ],
    factories_provider=get_telecom_factories,
    rag_docs_provider=get_telecom_rag_docs,
    defect_catalog=TELECOM_DEFECT_REGISTRY,
    regression_patterns=TELECOM_REGRESSION_MAP,
    metadata={
        "regulatory_standards": ["3GPP TS 32.240", "FCC CPNI", "GSMA PRD IR.21"],
        "primary_protocol": "5G-NR / Diameter / 3GPP Gy",
        "network_generations": ["4G-LTE", "5G-NR", "VoLTE"],
    },
)

# Auto-register with central platform registry
domain_registry.register(telecom_domain_pack)
