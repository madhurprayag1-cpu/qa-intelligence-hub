"""Healthcare Domain Synthetic Test Data Factories.

Adheres strictly to AGENTS.md Section 12, docs/ROADMAP.md Task 7.1:
- Reuses PersonGenerator and IdentifierGenerator from core base_factories.py.
- 100% synthetic, deterministic, and safe for portfolio demonstrations.
- Strictly adheres to HIPAA Safe Harbor: never uses real patient PHI or confidential records.
- Generates compliant HL7 FHIR R4 JSON payloads and clinical edge cases.
"""

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from base_factories import IdentifierGenerator, PersonGenerator
from domains.healthcare.models import (
    FHIRAddress,
    FHIRAppointment,
    FHIRAppointmentParticipant,
    FHIRCodeableConcept,
    FHIRCoding,
    FHIRHumanName,
    FHIRIdentifier,
    FHIRObservation,
    FHIRPatient,
    FHIRQuantity,
    FHIRTelecom,
    HIPAAMasker,
)


@dataclass
class SyntheticPatient:
    """Synthetic Patient Entity for Healthcare QA."""
    mrn: str
    first_name: str
    last_name: str
    full_name: str
    gender: str
    birth_date: str
    email: str
    phone: str
    ssn_masked: str
    insurance_id: str
    primary_practitioner_id: str = "PRAC-HC-001"


class PatientFactory:
    """Deterministic Synthetic Patient Generator (HIPAA Safe Harbor Compliant)."""

    _FIRST_NAMES_MALE = ["James", "David", "Michael", "Robert", "John", "Alexander", "Dimitris"]
    _FIRST_NAMES_FEMALE = ["Mary", "Jennifer", "Sarah", "Elena", "Sofia", "Maria", "Emily"]
    _LAST_NAMES = ["Papadopoulos", "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller"]

    @classmethod
    def build(
        cls,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        gender: Optional[str] = None,
        birth_date: Optional[str] = None,
        index: int = 0,
    ) -> SyntheticPatient:
        gen = gender or ("female" if index % 2 == 0 else "male")
        first_pool = cls._FIRST_NAMES_FEMALE if gen == "female" else cls._FIRST_NAMES_MALE
        first = first_name or first_pool[index % len(first_pool)]
        last = last_name or cls._LAST_NAMES[index % len(cls._LAST_NAMES)]
        full = f"{first} {last}"

        safe_tag = secrets.token_hex(2)
        email = f"{first.lower()}.{last.lower()}.{safe_tag}@qahub-health.io"
        phone = f"+155501{index:04d}"
        mrn = f"MRN-HC-{100000 + index:06d}"
        bdate = birth_date or f"{1960 + (index % 40):04d}-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
        ssn_masked = f"***-**-{1000 + (index * 13) % 9000:04d}"
        ins_id = f"INS-MED-{800000 + index:06d}"

        return SyntheticPatient(
            mrn=mrn,
            first_name=first,
            last_name=last,
            full_name=full,
            gender=gen,
            birth_date=bdate,
            email=email,
            phone=phone,
            ssn_masked=ssn_masked,
            insurance_id=ins_id,
        )

    @classmethod
    def build_batch(cls, count: int) -> List[SyntheticPatient]:
        return [cls.build(index=i) for i in range(count)]

    @classmethod
    def build_fhir_patient(
        cls,
        patient: Optional[SyntheticPatient] = None,
        index: int = 0,
    ) -> Dict[str, Any]:
        """Builds a standard HL7 FHIR Release 4 Patient resource dictionary."""
        p = patient or cls.build(index=index)
        return {
            "resourceType": "Patient",
            "id": p.mrn,
            "active": True,
            "identifier": [
                {
                    "use": "official",
                    "type_code": "MR",
                    "system": "http://qahub.io/fhir/identifiers/mrn",
                    "value": p.mrn,
                },
                {
                    "use": "secondary",
                    "type_code": "INS",
                    "system": "http://qahub.io/fhir/identifiers/insurance",
                    "value": p.insurance_id,
                },
            ],
            "name": [
                {
                    "use": "official",
                    "family": p.last_name,
                    "given": [p.first_name],
                    "text": p.full_name,
                }
            ],
            "telecom": [
                {"system": "email", "value": p.email, "use": "home"},
                {"system": "phone", "value": p.phone, "use": "mobile"},
            ],
            "gender": p.gender,
            "birthDate": p.birth_date,
            "address": [
                {
                    "use": "home",
                    "line": ["100 Health Sciences Way"],
                    "city": "Boston",
                    "state": "MA",
                    "postalCode": "02115",
                    "country": "USA",
                }
            ],
            "ssn_masked": p.ssn_masked,
        }

    @classmethod
    def build_security_xss(cls) -> Dict[str, Any]:
        """Builds a patient resource containing an XSS injection payload in name."""
        xss_person = PersonGenerator.generate_xss(email_domain="qahub-health.io")
        p = cls.build(first_name=xss_person.first_name, last_name=xss_person.last_name)
        return cls.build_fhir_patient(p)

    @classmethod
    def build_boundary_elderly(cls) -> Dict[str, Any]:
        """Builds an elderly patient aged 92 (tests HIPAA 89+ age threshold)."""
        p = cls.build(first_name="Eleanor", last_name="Vance", birth_date="1932-05-14")
        return cls.build_fhir_patient(p)

    @classmethod
    def build_boundary_pediatric(cls) -> Dict[str, Any]:
        """Builds a pediatric patient aged 4 (tests clinical dosage rules)."""
        p = cls.build(first_name="Leo", last_name="Chen", birth_date="2022-08-20")
        return cls.build_fhir_patient(p)

    @classmethod
    def build_phi_leak_vulnerable(cls) -> Dict[str, Any]:
        """
        Builds a patient resource with an UNMASKED 9-digit SSN.
        Used to verify that the QA security scanner and HIPAA validator detect PHI leaks.
        """
        fhir_res = cls.build_fhir_patient()
        fhir_res["ssn_raw"] = "123-45-6789"  # Deliberate unmasked leak for defect simulation
        fhir_res["ssn_masked"] = "123-45-6789"
        return fhir_res

    @classmethod
    def build_invalid_missing_name(cls) -> Dict[str, Any]:
        """Builds a patient resource missing the required 'name' element."""
        res = cls.build_fhir_patient()
        res["name"] = []
        return res


class ObservationFactory:
    """Synthetic LOINC Clinical Observation Factory for Vital Signs & Labs."""

    LOINC_BLOOD_PRESSURE = "85354-9"
    LOINC_SYSTOLIC = "8480-6"
    LOINC_DIASTOLIC = "8462-4"
    LOINC_HEART_RATE = "8867-4"
    LOINC_OXYGEN_SAT = "59408-5"
    LOINC_GLUCOSE = "2339-0"

    @classmethod
    def build_vital_signs(
        cls,
        patient_id: str,
        heart_rate: float = 72.0,
        systolic: float = 120.0,
        diastolic: float = 80.0,
        spo2: float = 98.0,
        recorded_at: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Builds a standard panel of vital sign FHIR Observations."""
        ts = recorded_at or datetime.utcnow().isoformat() + "Z"

        # 1. Heart Rate Observation
        hr_obs = {
            "resourceType": "Observation",
            "id": f"OBS-HR-{secrets.token_hex(3)}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": cls.LOINC_HEART_RATE,
                        "display": "Heart rate",
                    }
                ],
                "text": "Heart rate",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": ts,
            "valueQuantity": {
                "value": heart_rate,
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        }

        # 2. Blood Pressure Panel Observation
        bp_obs = {
            "resourceType": "Observation",
            "id": f"OBS-BP-{secrets.token_hex(3)}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": cls.LOINC_BLOOD_PRESSURE,
                        "display": "Blood pressure panel with all children optional",
                    }
                ],
                "text": "Blood Pressure",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": ts,
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": cls.LOINC_SYSTOLIC,
                                "display": "Systolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": systolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": cls.LOINC_DIASTOLIC,
                                "display": "Diastolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": diastolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
            ],
        }

        # 3. Oxygen Saturation (SpO2) Observation
        spo2_obs = {
            "resourceType": "Observation",
            "id": f"OBS-SPO2-{secrets.token_hex(3)}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": cls.LOINC_OXYGEN_SAT,
                        "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
                    }
                ],
                "text": "Oxygen Saturation",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": ts,
            "valueQuantity": {
                "value": spo2,
                "unit": "%",
                "system": "http://unitsofmeasure.org",
                "code": "%",
            },
        }

        return [hr_obs, bp_obs, spo2_obs]

    @classmethod
    def build_hypertensive_crisis(cls, patient_id: str) -> List[Dict[str, Any]]:
        """Builds an acute hypertensive crisis observation (BP 185/115 mmHg)."""
        return cls.build_vital_signs(
            patient_id=patient_id,
            heart_rate=118.0,
            systolic=185.0,
            diastolic=115.0,
            spo2=96.0,
        )

    @classmethod
    def build_hypoxemia_alert(cls, patient_id: str) -> List[Dict[str, Any]]:
        """Builds a critical hypoxemia observation (SpO2 86%)."""
        return cls.build_vital_signs(
            patient_id=patient_id,
            heart_rate=125.0,
            systolic=110.0,
            diastolic=70.0,
            spo2=86.0,
        )


class AppointmentFactory:
    """Synthetic Clinical Appointment Scheduling Factory."""

    @classmethod
    def build(
        cls,
        patient_id: str,
        practitioner_id: str = "PRAC-HC-001",
        start_time: Optional[str] = None,
        duration_minutes: int = 30,
    ) -> Dict[str, Any]:
        start_dt = datetime.fromisoformat(start_time) if start_time else datetime.utcnow() + timedelta(days=2)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        return {
            "resourceType": "Appointment",
            "id": f"APPT-HC-{secrets.token_hex(3).upper()}",
            "status": "booked",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "description": "Routine Clinical Follow-up",
            "participant": [
                {
                    "actor": {"reference": f"Patient/{patient_id}"},
                    "required": "required",
                    "status": "accepted",
                },
                {
                    "actor": {"reference": f"Practitioner/{practitioner_id}"},
                    "required": "required",
                    "status": "accepted",
                },
            ],
        }

    @classmethod
    def build_conflicting_slot(
        cls,
        base_appointment: Dict[str, Any],
        new_patient_id: str = "MRN-HC-CONFLICT",
    ) -> Dict[str, Any]:
        """Creates an appointment with the identical practitioner and overlapping slot."""
        practitioner_ref = "Practitioner/PRAC-HC-001"
        for p in base_appointment.get("participant", []):
            if "Practitioner" in p.get("actor", {}).get("reference", ""):
                practitioner_ref = p["actor"]["reference"]
                break

        return {
            "resourceType": "Appointment",
            "id": f"APPT-HC-CONFLICT-{secrets.token_hex(2).upper()}",
            "status": "booked",
            "start": base_appointment["start"],
            "end": base_appointment["end"],
            "description": "Simulated Conflicting Appointment",
            "participant": [
                {
                    "actor": {"reference": f"Patient/{new_patient_id}"},
                    "required": "required",
                    "status": "accepted",
                },
                {
                    "actor": {"reference": practitioner_ref},
                    "required": "required",
                    "status": "accepted",
                },
            ],
        }


class ClinicalDosageCalculator:
    """Clinical Pediatric Weight-Based Dosage Engine with Simulation Hooks."""

    @classmethod
    def calculate(
        cls,
        weight_kg: float,
        mg_per_kg: float,
        frequency_hours: int = 8,
        simulate_rounding_defect: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates exact pediatric single dose and daily total.
        If simulate_rounding_defect is True (DEF-HC-004), applies integer truncation,
        causing dangerous sub-therapeutic underdosing.
        """
        exact_single_dose = weight_kg * mg_per_kg
        doses_per_day = 24 // frequency_hours

        if simulate_rounding_defect:
            # Defect: Truncates to nearest 10mg integer floor instead of exact float
            calculated_dose = float(int(exact_single_dose // 10) * 10)
        else:
            calculated_dose = round(exact_single_dose, 2)

        daily_total = round(calculated_dose * doses_per_day, 2)
        precision_verified = abs(calculated_dose - exact_single_dose) < 0.01

        return {
            "patient_weight_kg": weight_kg,
            "recommended_mg_per_kg": mg_per_kg,
            "single_dose_mg": calculated_dose,
            "daily_total_mg": daily_total,
            "frequency_hours": frequency_hours,
            "precision_verified": precision_verified,
            "warning": None if precision_verified else "ARITHMETIC_PRECISION_DRIFT_DETECTED",
        }
