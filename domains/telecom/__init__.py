"""Telecom / 5G Mobile & BSS/OSS Domain Pack.

Adheres strictly to AGENTS.md Sections 1-4, 5, 8, 9, 10, 14, 21, and 40:
- Production-grade domain pack for Telecommunications, 5G Mobile, and BSS/OSS Charging.
- Subscriptions, SIM Card lifecycle, Plans, CDR (Call Detail Record) Rating, and FUP throttling.
- Intentional defect catalog DEF-TC-001 through DEF-TC-006.
- 100% synthetic, public-safe test data generators.
"""

from domains.telecom.models import (
    CallDetailRecord,
    CallType,
    DataPlan,
    RatingEngine,
    RatingZone,
    SIMCard,
    Subscriber,
    SubscriptionStatus,
)
from domains.telecom.defects import TELECOM_DEFECT_REGISTRY, TelecomDefectType
from domains.telecom.factories import (
    CDRFactory,
    PlanFactory,
    SIMFactory,
    SubscriberFactory,
    get_telecom_factories,
)
from domains.telecom.knowledge import TELECOM_KNOWLEDGE_DOCS, get_telecom_rag_docs
from domains.telecom.regression_map import TELECOM_REGRESSION_MAP

__all__ = [
    "CallDetailRecord",
    "CallType",
    "DataPlan",
    "RatingEngine",
    "RatingZone",
    "SIMCard",
    "Subscriber",
    "SubscriptionStatus",
    "TELECOM_DEFECT_REGISTRY",
    "TelecomDefectType",
    "CDRFactory",
    "PlanFactory",
    "SIMFactory",
    "SubscriberFactory",
    "get_telecom_factories",
    "TELECOM_KNOWLEDGE_DOCS",
    "get_telecom_rag_docs",
    "TELECOM_REGRESSION_MAP",
]
