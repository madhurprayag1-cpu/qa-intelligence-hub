"""Domain Pack Architecture & Dynamic Domain Registry.

Adheres strictly to the Master Architecture Directive:
- Reusable QA platform core with pluggable domain packs.
- Pluggable domain registry with zero hardcoded switch/if-else logic.
- Dynamic domain pack registration: any industry (Airline, Healthcare, E-commerce,
  Telecom, Banking/FinTech, Insurance, Logistics, etc.) can be plugged in without
  modifying core engine code.
- Active domain selectable via QA_DOMAIN environment variable (defaults to 'airline').
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class DomainCapability(str, Enum):
    """Standardized QA capabilities supported across domain packs."""
    UI_AUTOMATION = "ui_automation"
    API_TESTING = "api_testing"
    DATABASE_TESTING = "database_testing"
    CONTRACT_TESTING = "contract_testing"
    RAG_AI = "rag_ai"
    AGENTIC_QA = "agentic_qa"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_BENCHMARK = "performance_benchmark"
    QUALITY_GATE = "quality_gate"
    DEFECT_INJECTION = "defect_injection"


@dataclass
class DomainPack:
    """
    Standard interface contract for domain packs.
    Every industry domain (Phase 1 Airline, future Healthcare, E-commerce, Telecom,
    FinTech, etc.) implements this contract to plug into the QA Intelligence Hub.
    """
    domain_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[DomainCapability] = field(default_factory=list)
    rag_sources: List[str] = field(default_factory=list)
    defect_catalog: Dict[str, str] = field(default_factory=dict)
    regression_patterns: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    factories_provider: Optional[Callable[[], Any]] = None
    rag_docs_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None

    def has_capability(self, capability: DomainCapability | str) -> bool:
        cap_val = capability.value if isinstance(capability, DomainCapability) else capability
        return any(c.value == cap_val if isinstance(c, DomainCapability) else c == cap_val for c in self.capabilities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": [c.value if isinstance(c, DomainCapability) else str(c) for c in self.capabilities],
            "rag_sources": self.rag_sources,
            "defect_count": len(self.defect_catalog),
            "metadata": self.metadata,
        }


class UnsupportedDomainError(ValueError):
    """Raised when an unrecognized or unsupported domain is selected or validated."""
    pass


class DomainRegistry:
    """
    Central discovery and lifecycle manager for Domain Packs.
    Decouples the QA platform from domain-specific business rules.
    """

    def __init__(self, default_domain: str = "airline"):
        self._registry: Dict[str, DomainPack] = {}
        self._default_domain = default_domain.strip().lower()
        self._runtime_override: Optional[str] = None

    def register(self, pack: DomainPack) -> None:
        """Dynamically registers a domain pack into the platform."""
        self._registry[pack.domain_id.lower()] = pack

    def unregister(self, domain_id: str) -> Optional[DomainPack]:
        """Removes a domain pack from the registry."""
        return self._registry.pop(domain_id.lower(), None)

    def get(self, domain_id: str) -> Optional[DomainPack]:
        """Retrieves a registered domain pack by identifier."""
        return self._registry.get(domain_id.lower())

    def list_domains(self) -> List[DomainPack]:
        """Lists all registered domain packs."""
        return list(self._registry.values())

    def list_domain_ids(self) -> List[str]:
        """Lists IDs of all registered domain packs."""
        return list(self._registry.keys())

    def is_domain_supported(self, domain_id: str) -> bool:
        """Checks if a domain pack is registered."""
        if not domain_id or not isinstance(domain_id, str):
            return False
        return domain_id.strip().lower() in self._registry

    def validate_domain(self, domain_id: str) -> str:
        """Validates if domain_id is supported. Returns normalized domain_id or raises UnsupportedDomainError."""
        if not domain_id or not isinstance(domain_id, str):
            raise UnsupportedDomainError("Domain identifier must be a non-empty string.")
        norm = domain_id.strip().lower()
        if norm not in self._registry:
            supported = sorted(list(self._registry.keys()))
            raise UnsupportedDomainError(
                f"Unsupported domain '{domain_id}'. Supported domains: {supported}"
            )
        return norm

    def set_active_domain(self, domain_id: str) -> str:
        """Explicitly sets the active runtime domain. Validates domain or raises UnsupportedDomainError."""
        validated = self.validate_domain(domain_id)
        self._runtime_override = validated
        return validated

    def reset_active_domain(self) -> None:
        """Clears runtime domain override, returning to environment/default domain resolution."""
        self._runtime_override = None

    def get_active_domain_id(self, strict: bool = False) -> str:
        """
        Determines active domain:
        1. Explicit runtime override (via set_active_domain)
        2. QA_DOMAIN environment variable
        3. Default domain ('airline')

        If strict=True and configured domain is unsupported, raises UnsupportedDomainError.
        If strict=False, falls back to default domain.
        """
        candidate = self._runtime_override
        if candidate is None:
            raw_env = os.environ.get("QA_DOMAIN")
            if raw_env is not None and raw_env.strip():
                candidate = raw_env.strip().lower()
            else:
                candidate = self._default_domain

        if candidate in self._registry:
            return candidate

        if strict:
            supported = sorted(list(self._registry.keys()))
            raise UnsupportedDomainError(
                f"Active domain '{candidate}' is not supported. Supported domains: {supported}"
            )
        return self._default_domain

    def get_active_domain(self, strict: bool = False) -> Optional[DomainPack]:
        """Retrieves the active DomainPack instance."""
        active_id = self.get_active_domain_id(strict=strict)
        return self.get(active_id)

    def get_active_factories(self) -> Dict[str, Any]:
        """Resolves factories bound to the active domain pack."""
        pack = self.get_active_domain()
        if pack and pack.factories_provider:
            return pack.factories_provider()
        return {}

    def get_active_rag_docs(self) -> List[Dict[str, Any]]:
        """Resolves RAG knowledge documents bound to the active domain pack."""
        pack = self.get_active_domain()
        if pack and pack.rag_docs_provider:
            return pack.rag_docs_provider()
        return []

    def get_domain_summary(self) -> Dict[str, Any]:
        """Returns diagnostic overview of domain runtime status."""
        active = self.get_active_domain()
        return {
            "active_domain": self.get_active_domain_id(),
            "default_domain": self._default_domain,
            "registered_domains": self.list_domain_ids(),
            "active_capabilities": [
                c.value if hasattr(c, "value") else str(c)
                for c in (active.capabilities if active else [])
            ],
            "active_defect_count": len(active.defect_catalog) if active else 0,
            "runtime_override_active": self._runtime_override is not None,
        }

    def auto_discover(self) -> None:
        """Dynamically imports and registers installed domain packages."""
        import importlib
        for pkg_name in ("airline", "healthcare", "fintech", "ecommerce", "telecom"):
            try:
                importlib.import_module(f"domains.{pkg_name}.domain_pack")
            except Exception:
                pass


# Global platform domain registry instance
domain_registry = DomainRegistry(default_domain="airline")
domain_registry.auto_discover()
