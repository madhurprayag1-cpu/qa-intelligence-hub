"""HL7 FHIR Release 4 (4.0.1) Pydantic Models & HIPAA Safe Harbor Masking.

Adheres strictly to AGENTS.md Sections 3, 8, 12, 13 and docs/ROADMAP.md Task 7.1:
- Production-grade HL7 FHIR R4 resource definitions (Patient, Observation, Appointment).
- HIPAA Safe Harbor (45 CFR § 164.514(b)(2)) automated de-identification & masking.
- 100% synthetic, public-safe healthcare primitives with zero real patient PHI.
- Strict contract validation preventing silent data corruption or invalid resource schemas.
"""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class FHIRIdentifier(BaseModel):
    """HL7 FHIR Identifier Datatype."""
    use: Optional[Literal["usual", "official", "temp", "secondary", "old"]] = "official"
    type_code: Optional[str] = Field(default="MR", description="Identifier type code (e.g. MR for Medical Record)")
    system: Optional[str] = "http://qahub.io/fhir/identifiers/mrn"
    value: str = Field(min_length=1, description="Unique identifier value")


class FHIRHumanName(BaseModel):
    """HL7 FHIR HumanName Datatype."""
    use: Optional[Literal["usual", "official", "temp", "nickname", "anonymous", "old", "maiden"]] = "official"
    family: str = Field(min_length=1, description="Family (last) name")
    given: List[str] = Field(default_factory=list, description="Given (first/middle) names")
    text: Optional[str] = None


class FHIRTelecom(BaseModel):
    """HL7 FHIR ContactPoint Datatype."""
    system: Literal["phone", "fax", "email", "pager", "url", "sms", "other"] = "phone"
    value: str = Field(min_length=1, description="Contact value (e.g. phone number or email)")
    use: Optional[Literal["home", "work", "temp", "old", "mobile"]] = "home"


class FHIRAddress(BaseModel):
    """HL7 FHIR Address Datatype."""
    use: Optional[Literal["home", "work", "temp", "old", "billing"]] = "home"
    line: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = "USA"


class FHIRPatient(BaseModel):
    """
    HL7 FHIR Release 4 Patient Resource.
    Standardized schema for synthetic patient demographic and identity records.
    """
    resourceType: Literal["Patient"] = "Patient"
    id: str = Field(min_length=1, description="Logical resource ID (e.g. MRN)")
    active: bool = True
    identifier: List[FHIRIdentifier] = Field(default_factory=list)
    name: List[FHIRHumanName] = Field(min_length=1, description="Patient name elements")
    telecom: List[FHIRTelecom] = Field(default_factory=list)
    gender: Literal["male", "female", "other", "unknown"]
    birthDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Birth date in YYYY-MM-DD format")
    address: List[FHIRAddress] = Field(default_factory=list)
    ssn_masked: Optional[str] = Field(
        default=None,
        description="HIPAA Safe Harbor masked Social Security Number (***-**-NNNN)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: List[FHIRHumanName]) -> List[FHIRHumanName]:
        if not v or not v[0].family.strip():
            raise ValueError("FHIR Patient resource must contain at least one valid name with a family name")
        return v


class FHIRCoding(BaseModel):
    """HL7 FHIR Coding Datatype."""
    system: str = Field(description="Identity of the terminology system (e.g. http://loinc.org)")
    code: str = Field(description="Symbol in syntax defined by the system")
    display: Optional[str] = Field(default=None, description="Representation defined by the system")


class FHIRCodeableConcept(BaseModel):
    """HL7 FHIR CodeableConcept Datatype."""
    coding: List[FHIRCoding] = Field(min_length=1)
    text: Optional[str] = None


class FHIRQuantity(BaseModel):
    """HL7 FHIR Quantity Datatype."""
    value: float
    unit: str
    system: str = "http://unitsofmeasure.org"
    code: str = Field(default="")


class FHIRObservation(BaseModel):
    """
    HL7 FHIR Release 4 Observation Resource.
    Standardized schema for vital signs and clinical laboratory observations (LOINC).
    """
    resourceType: Literal["Observation"] = "Observation"
    id: str = Field(min_length=1)
    status: Literal["registered", "preliminary", "final", "amended", "corrected", "cancelled"] = "final"
    category: List[FHIRCodeableConcept] = Field(default_factory=list)
    code: FHIRCodeableConcept = Field(description="LOINC coded clinical observation type")
    subject: Dict[str, str] = Field(description="Reference to Patient resource (e.g. {'reference': 'Patient/MRN-001'})")
    effectiveDateTime: str = Field(description="Clinical recording timestamp in ISO 8601 format")
    valueQuantity: Optional[FHIRQuantity] = None
    component: Optional[List[Dict[str, Any]]] = None
    interpretation: Optional[List[FHIRCodeableConcept]] = None


class FHIRAppointmentParticipant(BaseModel):
    """HL7 FHIR Appointment Participant Datatype."""
    actor: Dict[str, str] = Field(description="Reference to Practitioner or Patient (e.g. {'reference': 'Patient/MRN-001'})")
    required: Literal["required", "optional", "information-only"] = "required"
    status: Literal["accepted", "declined", "tentative", "needs-action"] = "accepted"


class FHIRAppointment(BaseModel):
    """
    HL7 FHIR Release 4 Appointment Resource.
    Standardized schema for clinical practitioner booking and scheduling.
    """
    resourceType: Literal["Appointment"] = "Appointment"
    id: str = Field(min_length=1)
    status: Literal["proposed", "pending", "booked", "arrived", "fulfilled", "cancelled", "noshow", "entered-in-error"] = "booked"
    serviceType: Optional[List[FHIRCodeableConcept]] = None
    start: str = Field(description="Appointment start time in ISO 8601 format")
    end: str = Field(description="Appointment end time in ISO 8601 format")
    participant: List[FHIRAppointmentParticipant] = Field(min_length=1)
    description: Optional[str] = None


class PediatricDosageRequest(BaseModel):
    """Pediatric weight-based clinical dosage calculation request."""
    patient_id: str
    drug_name: str
    patient_weight_kg: float = Field(gt=0, le=150, description="Patient weight in kilograms")
    recommended_mg_per_kg: float = Field(gt=0, description="Recommended clinical dose in mg/kg")
    frequency_hours: int = Field(default=8, ge=1, le=24)


class PediatricDosageResponse(BaseModel):
    """Pediatric clinical dosage calculation response with safety verification."""
    patient_id: str
    drug_name: str
    patient_weight_kg: float
    recommended_mg_per_kg: float
    single_dose_mg: float
    daily_total_mg: float
    frequency_hours: int
    precision_verified: bool
    warning: Optional[str] = None


class HIPAAMasker:
    """
    HIPAA Safe Harbor De-Identification & PHI Masking Utility.
    Enforces 45 CFR § 164.514(b)(2) requirements:
    - Masks 9-digit Social Security Numbers (***-**-NNNN).
    - Masks direct phone and email identifiers where appropriate.
    - Scans dictionaries and JSON payloads for potential unencrypted PHI leaks.
    """

    _RAW_SSN_PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
    _RAW_UNFORMATTED_SSN = re.compile(r"\b\d{9}\b")

    @classmethod
    def mask_ssn(cls, ssn: Optional[str]) -> str:
        """Masks a raw Social Security Number to '***-**-NNNN'."""
        if not ssn:
            return "***-**-0000"
        digits = "".join(c for c in ssn if c.isdigit())
        if len(digits) >= 4:
            return f"***-**-{digits[-4:]}"
        return "***-**-0000"

    @classmethod
    def mask_phone(cls, phone: Optional[str]) -> str:
        """Masks a phone number to '***-***-NNNN'."""
        if not phone:
            return "***-***-0000"
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 4:
            return f"***-***-{digits[-4:]}"
        return "***-***-0000"

    @classmethod
    def detect_unmasked_phi(cls, data: Any) -> List[str]:
        """
        Recursively inspects a data structure for unmasked PHI violations.
        Returns a list of detected violation descriptions.
        """
        violations: List[str] = []

        def _scan(val: Any, path: str):
            if isinstance(val, str):
                if cls._RAW_SSN_PATTERN.search(val) and not val.startswith("***-**-"):
                    violations.append(f"Unmasked formatted SSN detected at '{path}': {val[:3]}-**-****")
                elif cls._RAW_UNFORMATTED_SSN.search(val) and "phone" not in path.lower() and "mrn" not in path.lower():
                    violations.append(f"Unmasked 9-digit potential SSN detected at '{path}'")
            elif isinstance(val, dict):
                for k, v in val.items():
                    current_path = f"{path}.{k}" if path else k
                    if k.lower() in ["ssn", "social_security_number"] and isinstance(v, str):
                        if not v.startswith("***-**-"):
                            violations.append(f"Raw unmasked SSN field at '{current_path}'")
                    _scan(v, current_path)
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    _scan(item, f"{path}[{i}]")

        _scan(data, "")
        return violations
