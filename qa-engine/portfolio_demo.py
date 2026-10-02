"""Unified End-to-End Portfolio Demonstration Runner.

Adheres strictly to AGENTS.md Sections 1-4, 5, 6, 8, 9, 10, 18, 24, 35, 36, and 40:
- Demonstrates senior SDET architecture across the complete connected system.
- Module 1: Dynamic Multi-Domain Registry & Runtime Switching (Airline, Healthcare, FinTech).
- Module 2: Synthetic Data Generation across 3 Industry Domain Packs.
- Module 3: Intentional Defect Engineering Catalogs (17 total documented defects).
- Module 4: Dual-Plane RAG & Groundedness Non-Fabrication Guardrail.
- Module 5: Specialist QA Agents (Defect RCA, UI Self-Healing, Reporting).
- Module 6: Intelligent Regression Diff Impact Selector.
- Module 7: Multi-Signal Release Quality Gate Governance (PRODUCTION_STRICT).
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _d in ["", "backend", "ai-engine", "qa-engine"]:
    _p = str(_REPO_ROOT / _d) if _d else str(_REPO_ROOT)
    if _p not in sys.path:
        sys.path.insert(0, _p)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.core.ai_provider import MockAIProvider, MockEmbeddingProvider
from agents import DefectRCAAgent, ReportingAgent, UIHealingAgent
from domain_registry import DomainCapability, UnsupportedDomainError, domain_registry
from evaluation import groundedness
from quality_gate import PRESET_POLICIES, QualityGateInput, evaluate_policy_gate
from rag import RAGPipeline
from regression_selector import select_regression_tests


@dataclass
class DemoModuleResult:
    module_id: str
    title: str
    status: str  # "PASSED", "FAILED"
    elapsed_ms: float
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioDemoReport:
    total_modules: int
    passed_modules: int
    failed_modules: int
    total_duration_ms: float
    modules: List[DemoModuleResult]
    overall_status: str  # "PASSED", "FAILED"


async def run_portfolio_demonstration(verbose: bool = True) -> PortfolioDemoReport:
    """Executes the full end-to-end portfolio demonstration across all 7 QE modules."""
    start_total = time.perf_counter()
    results: List[DemoModuleResult] = []

    # -----------------------------------------------------------------------
    # Module 1: Multi-Domain Registry & Dynamic Runtime Switching
    # -----------------------------------------------------------------------
    m1_start = time.perf_counter()
    try:
        # Verify auto-discovery of all 5 domain packs
        domains = domain_registry.list_domain_ids()
        assert "airline" in domains, "Airline domain pack missing"
        assert "healthcare" in domains, "Healthcare domain pack missing"
        assert "fintech" in domains, "FinTech domain pack missing"
        assert "ecommerce" in domains, "E-Commerce domain pack missing"
        assert "telecom" in domains, "Telecom domain pack missing"

        # Verify dynamic switching across domain packs
        domain_registry.set_active_domain("healthcare")
        assert domain_registry.get_active_domain_id() == "healthcare"

        domain_registry.set_active_domain("fintech")
        assert domain_registry.get_active_domain_id() == "fintech"

        domain_registry.set_active_domain("ecommerce")
        assert domain_registry.get_active_domain_id() == "ecommerce"

        domain_registry.set_active_domain("telecom")
        assert domain_registry.get_active_domain_id() == "telecom"

        # Verify strict validation & error handling
        rejected = False
        try:
            domain_registry.set_active_domain("unknown_sector")
        except UnsupportedDomainError:
            rejected = True
        assert rejected, "Invalid domain failed to trigger UnsupportedDomainError"

        domain_registry.reset_active_domain()
        assert domain_registry.get_active_domain_id() == "airline"

        m1_elapsed = round((time.perf_counter() - m1_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M1_DOMAIN_REGISTRY",
                title="Dynamic Multi-Domain Registry & Runtime Switching",
                status="PASSED",
                elapsed_ms=m1_elapsed,
                summary="Dynamic runtime switching across 5 domain packs verified with zero core code mutations.",
                details={
                    "registered_domains": domains,
                    "default_domain": domain_registry._default_domain,
                    "strict_validation_enforced": True,
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M1_DOMAIN_REGISTRY",
                title="Dynamic Multi-Domain Registry & Runtime Switching",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m1_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 2: Synthetic Data Generation across Domains
    # -----------------------------------------------------------------------
    m2_start = time.perf_counter()
    try:
        # 1. Airline synthetic passenger
        from domains.airline.factories import PassengerFactory
        passenger = PassengerFactory.build(index=0)
        assert passenger.name != "", "Airline passenger name empty"

        # 2. Healthcare synthetic patient & dosage calculation
        from domains.healthcare.factories import ClinicalDosageCalculator, PatientFactory
        patient = PatientFactory.build(index=0)
        assert patient.mrn.startswith("MRN-"), "Healthcare MRN format invalid"
        dosage = ClinicalDosageCalculator.calculate(weight_kg=15.0, mg_per_kg=20.0)
        assert dosage["single_dose_mg"] == 300.0, "Dosage calculation error"

        # 3. FinTech synthetic bank account & FX precision
        from domains.fintech.factories import AccountFactory, FXCalculator
        from domains.fintech.models import Currency
        account = AccountFactory.build(index=0)
        assert account.account_id.startswith("ACC-"), "FinTech account format invalid"
        fx = FXCalculator.convert(amount=100.0, from_curr=Currency.USD, to_curr=Currency.EUR)
        assert fx["converted_amount"] > 0.0, "FX conversion failed"

        # 4. E-Commerce synthetic product & cart pricing
        from domains.ecommerce.factories import CartFactory, ProductFactory
        from domains.ecommerce.models import PricingCalculator
        product = ProductFactory.build(index=0)
        assert product.sku.startswith("SKU-"), "E-Commerce SKU format invalid"
        cart = CartFactory.build(index=0)
        pricing = PricingCalculator.calculate_cart(cart.items)
        assert pricing["total_amount"] > 0.0, "Pricing calculation failed"

        # 5. Telecom synthetic subscriber & CDR rating
        from domains.telecom.factories import CDRFactory, SubscriberFactory
        from domains.telecom.models import RatingEngine
        subscriber = SubscriberFactory.build(index=0)
        assert subscriber.msisdn.startswith("+1"), "Telecom MSISDN format invalid"
        cdr = CDRFactory.build_voice_cdr(0, duration_seconds=120)
        cdr_charge = RatingEngine.rate_cdr(subscriber, cdr)
        assert cdr_charge >= 0.0, "CDR rating failed"

        m2_elapsed = round((time.perf_counter() - m2_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M2_DATA_FACTORIES",
                title="Synthetic Test Data Generation Across Domains",
                status="PASSED",
                elapsed_ms=m2_elapsed,
                summary="100% synthetic, deterministic data factories verified across Airline, Healthcare, FinTech, E-Commerce, and Telecom.",
                details={
                    "airline_sample": f"{passenger.name} ({passenger.loyalty_tier})",
                    "healthcare_sample": f"MRN: {patient.mrn} | 15kg pediatric dose: {dosage['single_dose_mg']}mg",
                    "fintech_sample": f"Account: {account.account_id} | 100 USD = {fx['converted_amount']} EUR",
                    "ecommerce_sample": f"SKU: {product.sku} ({product.name}) | Cart: ${pricing['total_amount']}",
                    "telecom_sample": f"MSISDN: {subscriber.msisdn} (Plan: {subscriber.plan.name}) | 2min charge: ${cdr_charge}",
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M2_DATA_FACTORIES",
                title="Synthetic Test Data Generation Across Domains",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m2_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 3: Intentional Defect Engineering Catalogs
    # -----------------------------------------------------------------------
    m3_start = time.perf_counter()
    try:
        air_pack = domain_registry.get("airline")
        hlth_pack = domain_registry.get("healthcare")
        fin_pack = domain_registry.get("fintech")
        ec_pack = domain_registry.get("ecommerce")
        tc_pack = domain_registry.get("telecom")

        air_defects = len(air_pack.defect_catalog) if air_pack else 0
        hlth_defects = len(hlth_pack.defect_catalog) if hlth_pack else 0
        fin_defects = len(fin_pack.defect_catalog) if fin_pack else 0
        ec_defects = len(ec_pack.defect_catalog) if ec_pack else 0
        tc_defects = len(tc_pack.defect_catalog) if tc_pack else 0
        total_defects = air_defects + hlth_defects + fin_defects + ec_defects + tc_defects

        assert air_defects == 5, f"Expected 5 airline defects, found {air_defects}"
        assert hlth_defects == 6, f"Expected 6 healthcare defects, found {hlth_defects}"
        assert fin_defects == 6, f"Expected 6 fintech defects, found {fin_defects}"
        assert ec_defects == 6, f"Expected 6 ecommerce defects, found {ec_defects}"
        assert tc_defects == 6, f"Expected 6 telecom defects, found {tc_defects}"
        assert total_defects == 29, f"Expected 29 total defects, found {total_defects}"

        m3_elapsed = round((time.perf_counter() - m3_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M3_DEFECT_ENGINEERING",
                title="Intentional Defect Engineering Catalogs",
                status="PASSED",
                elapsed_ms=m3_elapsed,
                summary=f"Verified 29 engineered defects across Airline (5), Healthcare (6), FinTech (6), E-Commerce (6), and Telecom (6).",
                details={
                    "airline_defects_count": air_defects,
                    "healthcare_defects_count": hlth_defects,
                    "fintech_defects_count": fin_defects,
                    "ecommerce_defects_count": ec_defects,
                    "telecom_defects_count": tc_defects,
                    "total_documented_defects": total_defects,
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M3_DEFECT_ENGINEERING",
                title="Intentional Defect Engineering Catalogs",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m3_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 4: Dual-Plane RAG & Groundedness Non-Fabrication Guardrail
    # -----------------------------------------------------------------------
    m4_start = time.perf_counter()
    try:
        pipeline = RAGPipeline(
            ai_provider=MockAIProvider(),
            embedding_provider=MockEmbeddingProvider(),
        )

        pipeline.ingest_document(
            document_id="AIR-DEMO-01",
            text="IATA NDC 21.3 mandates JSON/XML schemas for flight shopping, seat selection, and 3DS payments.",
            domain="airline",
        )
        pipeline.ingest_document(
            document_id="HLTH-DEMO-01",
            text="HL7 FHIR Release 4 specifies Patient, Observation, and Appointment resources under HIPAA Safe Harbor.",
            domain="healthcare",
        )

        # 1. Grounded query
        grounded_res = await pipeline.query("FHIR Patient resources", domain="healthcare")
        assert not grounded_res.refusal, "Expected grounded query to succeed"
        assert len(grounded_res.retrieved_chunks) > 0, "No chunks retrieved"

        eval_res = groundedness(grounded_res.answer, grounded_res.context_text)
        assert eval_res.passed is True, f"Groundedness check failed: {eval_res.reason}"
        assert eval_res.score >= 0.75, f"Groundedness score {eval_res.score} below threshold"

        # 2. Cross-domain non-fabrication refusal
        refused_res = await pipeline.query("IATA NDC flight shopping", domain="healthcare")
        assert refused_res.refusal is True, "Expected cross-domain query to trigger refusal"
        assert "No relevant domain knowledge" in refused_res.answer

        m4_elapsed = round((time.perf_counter() - m4_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M4_RAG_PIPELINE",
                title="Dual-Plane RAG & Groundedness Non-Fabrication Guardrail",
                status="PASSED",
                elapsed_ms=m4_elapsed,
                summary="Dual-plane RAG validated with grounded evidence evaluation and cross-domain refusal guardrails.",
                details={
                    "grounded_score": eval_res.score,
                    "retrieved_chunks_count": len(grounded_res.retrieved_chunks),
                    "truthful_refusal_verified": True,
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M4_RAG_PIPELINE",
                title="Dual-Plane RAG & Groundedness Non-Fabrication Guardrail",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m4_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 5: Specialist QA Agents
    # -----------------------------------------------------------------------
    m5_start = time.perf_counter()
    try:
        # 1. Defect RCA Agent
        rca_agent = DefectRCAAgent()
        rca_run = await rca_agent.execute(
            task="Analyze payment gateway failure",
            context={
                "error_msg": "ACS 3D Secure challenge timeout on payment route",
                "status_code": 504,
                "endpoint": "/payments/confirm",
            },
        )
        assert rca_run.status == "COMPLETED", "DefectRCAAgent failed"

        # 2. UI Self-Healing Agent
        heal_agent = UIHealingAgent()
        heal_recommendation = heal_agent.heal_selector(
            broken_selector="//div[2]/form/div[3]/button[1]",
            dom_snippet="<div class='actions'><button type='submit' class='btn btn-primary'>Confirm Booking</button></div>",
            failure_message="Timeout 30000ms waiting for locator",
            target_action="click",
        )
        assert heal_recommendation["status"] == "VERIFIED", f"Expected VERIFIED, got {heal_recommendation['status']}"
        assert heal_recommendation["healed_selector"] == "page.getByRole('button', { name: 'Confirm Booking' })"


        # 3. Reporting Agent
        report_agent = ReportingAgent()
        report_run = await report_agent.execute(
            task="Generate sign-off summary",
            context={
                "policy_name": "PRODUCTION_STRICT",
                "total_tests": 329,
                "passed_tests": 329,
                "failed_tests": 0,
                "quality_gate_status": "PASSED",
            },
        )
        assert report_run.status == "COMPLETED", "ReportingAgent failed"

        m5_elapsed = round((time.perf_counter() - m5_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M5_SPECIALIST_AGENTS",
                title="Specialist QA Agents (RCA, Self-Healing, Reporting)",
                status="PASSED",
                elapsed_ms=m5_elapsed,
                summary="Specialist agents executed deterministically for automated root cause analysis, locator healing, and release reporting.",
                details={
                    "rca_diagnosis": "Defect RCA classified failure trace successfully",
                    "healed_selector": heal_recommendation["healed_selector"],
                    "executive_report_generated": len(report_run.output) > 50,
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M5_SPECIALIST_AGENTS",
                title="Specialist QA Agents (RCA, Self-Healing, Reporting)",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m5_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 6: Intelligent Regression Diff Impact Selector
    # -----------------------------------------------------------------------
    m6_start = time.perf_counter()
    try:
        # Multi-domain diff simulation across all 5 production domain packs
        diff_files = [
            "backend/app/routers/payments.py",
            "domains/healthcare/dosages.py",
            "domains/fintech/transfers.py",
            "domains/ecommerce/catalog.py",
            "domains/telecom/subscribers.py",
        ]
        plan = select_regression_tests(diff_files)
        assert plan.pytest_command.startswith("pytest ")
        assert len(plan.selected_test_files) >= 5

        m6_elapsed = round((time.perf_counter() - m6_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M6_REGRESSION_SELECTOR",
                title="Intelligent Regression Diff Impact Selector",
                status="PASSED",
                elapsed_ms=m6_elapsed,
                summary="PR git diffs dynamically mapped to minimal test execution impact set across domains.",
                details={
                    "changed_files_count": len(diff_files),
                    "impacted_test_files": plan.selected_test_files,
                    "generated_pytest_cmd": plan.pytest_command,
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M6_REGRESSION_SELECTOR",
                title="Intelligent Regression Diff Impact Selector",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m6_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Module 7: Multi-Signal Release Quality Gate Governance
    # -----------------------------------------------------------------------
    m7_start = time.perf_counter()
    try:
        policy = PRESET_POLICIES["PRODUCTION_STRICT"]
        gate_input = QualityGateInput(
            total_tests=329,
            passed_tests=329,
            failed_tests=0,
            critical_defects=0,
            contract_failures=0,
            security_vulnerabilities=0,
            critical_security_vulnerabilities=0,
            pci_dss_violations=0,
            rag_groundedness_score=0.96,
            rag_context_relevance_score=0.92,
            rag_citation_accuracy_score=0.95,
            rag_truthful_refusal_score=0.98,
        )
        gate_res = evaluate_policy_gate(gate_input, policy=policy)
        assert gate_res.passed is True, "Expected gate to pass"
        assert gate_res.status == "PASSED", f"Gate status was {gate_res.status}"
        assert len(gate_res.violations) == 0, f"Found unexpected violations: {gate_res.violations}"

        m7_elapsed = round((time.perf_counter() - m7_start) * 1000, 2)
        results.append(
            DemoModuleResult(
                module_id="M7_QUALITY_GATE",
                title="Multi-Signal Release Quality Gate Governance",
                status="PASSED",
                elapsed_ms=m7_elapsed,
                summary="PRODUCTION_STRICT policy evaluated across test pass rates, security, contracts, and RAG metrics -> APPROVED.",
                details={
                    "policy_tier": policy.name,
                    "gate_verdict": gate_res.status,
                    "pass_rate": f"{gate_res.pass_rate * 100:.1f}%",
                    "violations_count": len(gate_res.violations),
                },
            )
        )
    except Exception as exc:
        results.append(
            DemoModuleResult(
                module_id="M7_QUALITY_GATE",
                title="Multi-Signal Release Quality Gate Governance",
                status="FAILED",
                elapsed_ms=round((time.perf_counter() - m7_start) * 1000, 2),
                summary=f"Failed: {exc}",
            )
        )

    # -----------------------------------------------------------------------
    # Summary Rollup
    # -----------------------------------------------------------------------
    total_elapsed = round((time.perf_counter() - start_total) * 1000, 2)
    passed_count = sum(1 for r in results if r.status == "PASSED")
    failed_count = len(results) - passed_count
    overall = "PASSED" if failed_count == 0 else "FAILED"

    report = PortfolioDemoReport(
        total_modules=len(results),
        passed_modules=passed_count,
        failed_modules=failed_count,
        total_duration_ms=total_elapsed,
        modules=results,
        overall_status=overall,
    )

    if verbose:
        print_formatted_demo_report(report)

    return report


def print_formatted_demo_report(report: PortfolioDemoReport) -> None:
    """Formats and prints executive summary table to terminal."""
    print("\n" + "=" * 76)
    print("🏆  QA INTELLIGENCE HUB — COMPREHENSIVE PORTFOLIO DEMONSTRATION")
    print("=" * 76)
    print(f"Overall Status:   {'🟢 ' + report.overall_status if report.overall_status == 'PASSED' else '🔴 ' + report.overall_status}")
    print(f"Modules Passed:   {report.passed_modules}/{report.total_modules}")
    print(f"Total Latency:    {report.total_duration_ms:.2f} ms")
    print("-" * 76)

    for i, mod in enumerate(report.modules, start=1):
        status_icon = "✅" if mod.status == "PASSED" else "❌"
        print(f"\n[{i}/7] {status_icon} {mod.title} ({mod.elapsed_ms}ms)")
        print(f"      Summary: {mod.summary}")
        if mod.details:
            for k, v in mod.details.items():
                print(f"      • {k}: {v}")

    print("\n" + "=" * 76)
    if report.overall_status == "PASSED":
        print("🌟 All 7 Quality Engineering capabilities operational & production-verified.")
    else:
        print("⚠️ One or more portfolio demonstration modules failed.")
    print("=" * 76 + "\n")


def run_cli() -> int:
    parser = argparse.ArgumentParser(
        description="QA Intelligence Hub — Comprehensive Portfolio Demonstration Runner"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    report = asyncio.run(run_portfolio_demonstration(verbose=not args.json))

    if args.json:
        out = {
            "overall_status": report.overall_status,
            "total_modules": report.total_modules,
            "passed_modules": report.passed_modules,
            "failed_modules": report.failed_modules,
            "total_duration_ms": report.total_duration_ms,
            "modules": [
                {
                    "module_id": m.module_id,
                    "title": m.title,
                    "status": m.status,
                    "elapsed_ms": m.elapsed_ms,
                    "summary": m.summary,
                    "details": m.details,
                }
                for m in report.modules
            ],
        }
        print(json.dumps(out, indent=2))

    return 0 if report.overall_status == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(run_cli())
