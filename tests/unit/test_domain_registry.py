"""Unit tests for DomainRegistry, DomainPack, and BaseFactories.

Adheres to Master Architecture Directive Step 1:
- Verifies dynamic domain registration without hardcoded switches.
- Verifies active domain defaults to 'airline'.
- Verifies QA_DOMAIN environment override.
- Verifies reusable synthetic generator primitives.
"""

import os
import pytest
from domain_registry import DomainCapability, DomainPack, DomainRegistry
from base_factories import (
    PersonGenerator,
    IdentifierGenerator,
    PaymentInstrumentGenerator,
    SecurityPayloadGenerator,
)


def test_domain_pack_capabilities():
    """Verify DomainPack capability checks."""
    pack = DomainPack(
        domain_id="test_domain",
        name="Test Domain",
        capabilities=[
            DomainCapability.UI_AUTOMATION,
            DomainCapability.API_TESTING,
            DomainCapability.RAG_AI,
        ],
    )
    assert pack.has_capability(DomainCapability.UI_AUTOMATION)
    assert pack.has_capability("ui_automation")
    assert pack.has_capability(DomainCapability.RAG_AI)
    assert not pack.has_capability(DomainCapability.SECURITY_AUDIT)


def test_domain_registry_lifecycle():
    """Verify registering, retrieving, and unregistering domain packs dynamically."""
    registry = DomainRegistry(default_domain="airline")

    # Register hypothetical FinTech domain pack
    fintech_pack = DomainPack(
        domain_id="fintech",
        name="FinTech / Digital Banking",
        version="1.0.0",
        capabilities=[DomainCapability.API_TESTING, DomainCapability.SECURITY_AUDIT],
        defect_catalog={"DEF-FT-01": "Double debit race condition"},
    )
    registry.register(fintech_pack)

    assert registry.is_domain_supported("fintech")
    assert registry.is_domain_supported("FINTECH")  # Case insensitive
    retrieved = registry.get("fintech")
    assert retrieved is not None
    assert retrieved.name == "FinTech / Digital Banking"
    assert retrieved.defect_catalog["DEF-FT-01"] == "Double debit race condition"

    # Unregister
    removed = registry.unregister("fintech")
    assert removed is not None
    assert not registry.is_domain_supported("fintech")


def test_active_domain_default_and_env(monkeypatch):
    """Verify default active domain is 'airline' and honors QA_DOMAIN override."""
    registry = DomainRegistry(default_domain="airline")
    airline_pack = DomainPack(domain_id="airline", name="Airline / NDC")
    ecommerce_pack = DomainPack(domain_id="ecommerce", name="E-Commerce")
    registry.register(airline_pack)
    registry.register(ecommerce_pack)

    # Default fallback
    monkeypatch.delenv("QA_DOMAIN", raising=False)
    assert registry.get_active_domain_id() == "airline"
    assert registry.get_active_domain().name == "Airline / NDC"

    # Override via environment variable
    monkeypatch.setenv("QA_DOMAIN", "ecommerce")
    assert registry.get_active_domain_id() == "ecommerce"
    assert registry.get_active_domain().name == "E-Commerce"

    # Invalid env value falls back to default
    monkeypatch.setenv("QA_DOMAIN", "nonexistent_domain")
    assert registry.get_active_domain_id() == "airline"


def test_base_factories_person_generator():
    """Verify generic PersonGenerator generates deterministic and safe synthetic data."""
    p1 = PersonGenerator.generate(index=0)
    p2 = PersonGenerator.generate(index=1)

    assert p1.full_name != p2.full_name
    assert "@qahub.io" in p1.email
    assert p1.country_code == "US"

    xss_p = PersonGenerator.generate_xss()
    assert "<script>" in xss_p.full_name

    long_p = PersonGenerator.generate_boundary_long(length=200)
    assert len(long_p.full_name) == 200


def test_base_factories_identifier_and_payments():
    """Verify identifier generator and PCI-safe payment instrument generator."""
    ref = IdentifierGenerator.generate_reference(prefix="ORD")
    assert ref.startswith("ORD-")
    assert len(ref) == 12

    card = PaymentInstrumentGenerator.generate_card(brand="MASTERCARD", requires_3ds=True)
    assert card["brand"] == "MASTERCARD"
    assert card["masked_pan"].startswith("****-****-****-")
    assert len(card["last_four"]) == 4
    assert card["requires_3ds"] is True
    assert card["token"].startswith("tok_synth_")

    sqli = SecurityPayloadGenerator.get_sqli_payload(0)
    assert "OR" in sqli or "DROP" in sqli or "UNION" in sqli


@pytest.mark.anyio
async def test_domain_aware_rag_partitioning():
    """Verify RAG pipeline partitions vector search across domains."""
    from rag import RAGPipeline
    from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider

    pipeline = RAGPipeline(
        ai_provider=MockAIProvider(),
        embedding_provider=MockEmbeddingProvider(),
    )

    # Ingest documents tagged with different domains
    pipeline.ingest_document(
        document_id="AIR-01",
        text="Airlines enforce IATA NDC 21.3 XML/JSON standards for flight shopping.",
        domain="airline",
    )
    pipeline.ingest_document(
        document_id="HLTH-01",
        text="Healthcare systems enforce HIPAA and HL7 FHIR standards for patient EHR records.",
        domain="healthcare",
    )

    # 1. Query with domain="airline" -> only airline chunks retrieved
    air_results = pipeline.retrieve("standards", domain="airline")
    assert len(air_results) > 0
    for chunk, _ in air_results:
        assert chunk.metadata.get("domain") == "airline"
        assert "Airlines" in chunk.text

    # 2. Query with domain="healthcare" -> only healthcare chunks retrieved
    hlth_results = pipeline.retrieve("standards", domain="healthcare")
    assert len(hlth_results) > 0
    for chunk, _ in hlth_results:
        assert chunk.metadata.get("domain") == "healthcare"
        assert "Healthcare" in chunk.text

    # 3. Query with domain=None -> both domains retrievable (backward compatible)
    all_results = pipeline.retrieve("standards", domain=None)
    domains_found = {c.metadata.get("domain") for c, _ in all_results}
    assert "airline" in domains_found
    assert "healthcare" in domains_found
