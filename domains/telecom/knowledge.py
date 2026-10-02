"""Domain RAG Knowledge Corpus for Telecommunications.

Adheres strictly to AGENTS.md Section 10 (RAG Architecture):
- Realistic telecom network policies, 3GPP standards, and BSS/OSS charging rules.
- Fully synthetic, standard-based documentation.
- Used for RAG retrieval evaluation, groundedness verification, and domain partitioning.
"""

from typing import Any, Dict, List

TELECOM_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    {
        "document_id": "TELECOM-FUP-01",
        "domain": "telecom",
        "title": "Fair Usage Policy (FUP) & Bandwidth Throttling Standards",
        "text": (
            "Under the 5G Fair Usage Policy (FUP), unlimited data plans include an unthrottled high-speed quota "
            "up to 50GB per billing cycle. Once the subscriber exceeds 50GB of cumulative data transfer, bandwidth "
            "is automatically shaped to a maximum throughput of 128 kbps for remaining traffic. Video streaming is "
            "capped at 480p resolution while throttled. High-speed capacity automatically resets at 00:00:00 UTC "
            "on the first calendar day of the next billing cycle. Subscribers may purchase high-speed speed passes "
            "to restore unshaped 5G connectivity immediately without waiting for billing reset."
        ),
        "metadata": {
            "category": "bandwidth_policy",
            "fup_threshold_gb": 50.0,
            "throttled_speed_kbps": 128,
            "version": "2026.1",
        },
    },
    {
        "document_id": "TELECOM-ROAMING-01",
        "domain": "telecom",
        "title": "International Roaming Tariffs and Zone Governance",
        "text": (
            "International roaming requires active roaming authorization on the subscriber profile. "
            "Rating Zone 1 comprises Canada, Mexico, European Union member states, and the United Kingdom, "
            "where voice calls are billed at $0.50/minute and data at $0.05/MB. Rating Zone 2 comprises Asia-Pacific, "
            "Latin America, and the Middle East, billed at $1.50/minute and $0.20/MB. Maritime and satellite networks "
            "are classified as Special Zone 3 ($4.00/min, $1.00/MB). If a subscriber with roaming_allowed=False "
            "attempts network attachment or CDR generation in a foreign VPLMN (Visited Public Land Mobile Network), "
            "the BSS must immediately reject the session with error code TEL-ERR-ROAMING-NOT-ALLOWED."
        ),
        "metadata": {
            "category": "roaming_tariffs",
            "standards": ["3GPP TS 22.011", "GSMA PRD IR.21"],
            "version": "3.4",
        },
    },
    {
        "document_id": "TELECOM-BILLING-01",
        "domain": "telecom",
        "title": "Real-Time Online Charging System (OCS) & CDR Rating Architecture",
        "text": (
            "In accordance with 3GPP TS 32.240 charging architecture, prepaid subscriptions are rated via "
            "the real-time Online Charging System (OCS) using the Gy/Diameter interface. Network elements "
            "request quota reservations prior to session establishment. If prepaid balance drops below the required "
            "reserve, the session is terminated. Postpaid subscriptions are rated asynchronously via the "
            "Offline Charging System (OFCS) and mediation pipeline. All Call Detail Records (CDRs) must be "
            "time-stamped in UTC, and fractional data usage must be computed to byte-level precision before applying "
            "cents-per-MB rating."
        ),
        "metadata": {
            "category": "charging_architecture",
            "standards": ["3GPP TS 32.240", "3GPP TS 32.299"],
            "version": "4.0",
        },
    },
    {
        "document_id": "TELECOM-PORTABILITY-01",
        "domain": "telecom",
        "title": "Mobile Number Portability (MNP) & PAC Governance",
        "text": (
            "Mobile Number Portability (MNP) allows subscribers to retain their MSISDN when switching mobile "
            "network operators. The donor network must issue a Porting Authorisation Code (PAC) within 2 hours "
            "of customer request via SMS. PAC codes remain valid for exactly 30 calendar days from issuance. "
            "Upon submission to the recipient operator, the number porting transfer must complete on the next "
            "business day. During porting, the subscriber line remains in PENDING_ACTIVATION until the donor "
            "network confirms routing release. Cancelled or terminated lines with active balance disputes cannot be ported."
        ),
        "metadata": {
            "category": "portability_regulations",
            "pac_validity_days": 30,
            "porting_sla_hours": 24,
            "version": "1.2",
        },
    },
    {
        "document_id": "TELECOM-CDR-SLA-01",
        "domain": "telecom",
        "title": "CDR Reconciliation, Deduplication, and Audit Governance",
        "text": (
            "The mediation engine must enforce strict CDR deduplication over a 72-hour sliding window based on the "
            "composite key: {imsi, start_time_epoch, destination, duration_seconds}. Any incoming CDR matching an "
            "already processed key within the window must be quarantined as DUPLICATE_USAGE and rejected from billing "
            "to prevent double charging. CDR audit logs must mask the last 4 digits of the MSISDN and all but the first "
            "6 digits of the IMSI in accordance with FCC CPNI privacy rules and GDPR Article 32."
        ),
        "metadata": {
            "category": "reconciliation_sla",
            "dedup_window_hours": 72,
            "compliance": ["FCC CPNI", "GDPR Art 32"],
            "version": "2.1",
        },
    },
]


def get_telecom_rag_docs() -> List[Dict[str, Any]]:
    """Returns knowledge documents for RAG indexing."""
    return TELECOM_KNOWLEDGE_DOCS
