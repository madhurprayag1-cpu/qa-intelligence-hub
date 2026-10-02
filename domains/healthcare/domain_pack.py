"""Healthcare Domain Pack Definition & Registration.

Adheres strictly to the Master Architecture Directive & AGENTS.md Sections 1-4:
- Implements DomainPack protocol for Healthcare / HL7 FHIR & Clinical Systems.
- Auto-registers with the central domain_registry.
- Encapsulates domain capabilities, RAG sources, defect catalog, regression patterns, and metadata.
"""

from domain_registry import DomainCapability, DomainPack, domain_registry
from domains.healthcare.defects import HEALTHCARE_DEFECT_REGISTRY
from domains.healthcare.knowledge import get_healthcare_knowledge_docs
from domains.healthcare.regression_map import HEALTHCARE_REGRESSION_PATTERNS


def get_healthcare_factories():
    from domains.healthcare.factories import (
        PatientFactory,
        ObservationFactory,
        AppointmentFactory,
        ClinicalDosageCalculator,
    )
    return {
        "PatientFactory": PatientFactory,
        "ObservationFactory": ObservationFactory,
        "AppointmentFactory": AppointmentFactory,
        "ClinicalDosageCalculator": ClinicalDosageCalculator,
    }


healthcare_domain_pack = DomainPack(
    domain_id="healthcare",
    name="Healthcare / HL7 FHIR & Clinical Systems",
    version="1.0.0",
    description="HL7 FHIR Release 4 interoperability, HIPAA Safe Harbor de-identification, vital signs observation, appointment scheduling, and pediatric clinical dosage calculation.",
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
        "HEALTHCARE-FHIR-01",
        "HEALTHCARE-HIPAA-01",
        "HEALTHCARE-CLINICAL-01",
        "HEALTHCARE-APPOINTMENT-01",
        "HEALTHCARE-DOSAGE-01",
    ],
    factories_provider=get_healthcare_factories,
    rag_docs_provider=get_healthcare_knowledge_docs,
    defect_catalog={
        d.code: f"{d.name}: {d.description}"
        for d in HEALTHCARE_DEFECT_REGISTRY.values()
    },
    regression_patterns=HEALTHCARE_REGRESSION_PATTERNS,
    metadata={
        "fhir_standard": "HL7 FHIR Release 4 (4.0.1)",
        "hipaa_compliance_mode": "Strict Safe Harbor (45 CFR § 164.514)",
        "coding_systems": ["LOINC", "SNOMED-CT", "UCUM", "ICD-10-CM"],
        "supported_resources": ["Patient", "Observation", "Appointment"],
        "safe_harbor_identifiers_count": 18,
    },
)

# Auto-register with central platform registry
domain_registry.register(healthcare_domain_pack)
