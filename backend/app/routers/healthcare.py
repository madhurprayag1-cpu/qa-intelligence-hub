"""Healthcare Clinical REST API & SUT Router.

Adheres strictly to AGENTS.md Sections 8, 9, 13, 21 and Phase 1B Blueprint:
- Production-grade synthetic SUT endpoints for HL7 FHIR R4 Patient, Observation, and Appointment resources.
- Safe Harbor de-identification, clinical validation, and pediatric dosage calculation.
- Dual-plane execution: PostgreSQL persistence via SQLAlchemy models + in-memory hermetic cache.
- Strict tenant isolation with owner_user_id enforcing IDOR boundaries.
- Realistic defect injection hooks for QA demonstration (DEF-HC-001 through DEF-HC-006).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import User, get_current_domain_user
from app.db.database import get_db
from app.models.healthcare import (
    HealthcareAppointmentModel,
    HealthcareObservationModel,
    HealthcarePatientModel,
)
from domains.healthcare.defects import HEALTHCARE_DEFECT_REGISTRY, HealthcareDefectType
from domains.healthcare.factories import ClinicalDosageCalculator
from domains.healthcare.models import (
    FHIRAppointment,
    FHIRObservation,
    FHIRPatient,
    HIPAAMasker,
    PediatricDosageRequest,
    PediatricDosageResponse,
)

router = APIRouter(prefix="/healthcare", tags=["healthcare-domain"])

# Hermetic in-memory store for synthetic healthcare SUT execution
_PATIENT_STORE: Dict[str, Dict[str, Any]] = {}
_OBSERVATION_STORE: List[Dict[str, Any]] = []
_APPOINTMENT_STORE: List[Dict[str, Any]] = []

SYNTHETIC_PRACTITIONERS = [
    {"id": "Practitioner/DR-CHEN-01", "name": "Dr. Sarah Chen, MD", "specialty": "Cardiology"},
    {"id": "Practitioner/DR-PATEL-02", "name": "Dr. Michael Patel, MD", "specialty": "Pediatrics"},
    {"id": "Practitioner/DR-KIM-03", "name": "Dr. Elena Kim, MD", "specialty": "General Practice"},
    {"id": "Practitioner/DR-GOMEZ-04", "name": "Dr. Carlos Gomez, MD", "specialty": "Neurology"},
]


def reset_healthcare_store() -> None:
    """Resets in-memory stores for hermetic test execution."""
    _PATIENT_STORE.clear()
    _OBSERVATION_STORE.clear()
    _APPOINTMENT_STORE.clear()


@router.post("/patients", status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: Dict[str, Any],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Ingests and validates a synthetic HL7 FHIR Release 4 Patient resource.
    Persists to PostgreSQL with tenant isolation (owner_user_id).
    Supports defect simulation:
    - FHIR_SCHEMA_VALIDATION_FAILURE: Bypasses schema validation, permitting invalid/empty names.
    - PHI_EXPOSURE_UNMASKED_SSN: Leaks unmasked 9-digit SSN in the response.
    """
    is_schema_defect = x_simulate_defect in (
        HealthcareDefectType.FHIR_SCHEMA_VALIDATION_FAILURE.value,
        "FHIR_SCHEMA_VALIDATION_FAILURE",
        "DEF-HC-002",
        "DEF-HC-005",
    )
    is_phi_defect = x_simulate_defect in (
        HealthcareDefectType.PHI_EXPOSURE_UNMASKED_SSN.value,
        "PHI_EXPOSURE_UNMASKED_SSN",
        "DEF-HC-001",
    )

    patient_id = patient_data.get("id") or f"MRN-HC-{len(_PATIENT_STORE) + 1:06d}"
    stored = dict(patient_data)
    stored["id"] = patient_id

    # Contract Schema Validation
    if not is_schema_defect:
        try:
            FHIRPatient.model_validate(stored)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"FHIR R4 Patient Contract Validation Failure: {exc}",
            )

    # HIPAA Safe Harbor Masking
    if is_phi_defect:
        stored["ssn_masked"] = patient_data.get("ssn_raw") or "123-45-6789"
    else:
        raw_ssn = patient_data.get("ssn_raw") or patient_data.get("ssn_masked")
        stored["ssn_masked"] = HIPAAMasker.mask_ssn(raw_ssn)

    raw_phone = None
    for tc in stored.get("telecom", []):
        if tc.get("system") == "phone":
            raw_phone = tc.get("value")
            tc["value"] = HIPAAMasker.mask_phone(raw_phone)
    if raw_phone:
        stored["phone_masked"] = HIPAAMasker.mask_phone(raw_phone)
    else:
        stored["phone_masked"] = "***-***-0000"

    _PATIENT_STORE[patient_id] = stored

    # Database Persistence
    try:
        names = patient_data.get("name", [])
        family_name = "Patient"
        given_names = ["Synthetic"]
        if names and isinstance(names, list) and len(names) > 0:
            family_name = names[0].get("family") or "Patient"
            given_names = names[0].get("given") or ["Synthetic"]

        birth_date = patient_data.get("birthDate") or patient_data.get("dob") or "1980-01-01"
        gender = patient_data.get("gender") or "unknown"
        phone = None
        email = None
        for tc in patient_data.get("telecom", []):
            if tc.get("system") == "phone":
                phone = tc.get("value")
            elif tc.get("system") == "email":
                email = tc.get("value")

        existing = db.get(HealthcarePatientModel, patient_id)
        if existing:
            existing.family_name = family_name
            existing.given_names = given_names
            existing.birth_date = birth_date
            existing.gender = gender
            existing.phone_masked = phone
            existing.email = email
            existing.ssn_masked = stored.get("ssn_masked")
            existing.active = True
        else:
            db_patient = HealthcarePatientModel(
                id=patient_id,
                owner_user_id=current_user.id,
                family_name=family_name,
                given_names=given_names,
                gender=gender,
                birth_date=birth_date,
                ssn_masked=stored.get("ssn_masked"),
                phone_masked=phone,
                email=email,
                active=True,
            )
            db.add(db_patient)
        db.commit()
    except Exception:
        db.rollback()

    return stored


@router.get("/patients")
async def list_patients(
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists patients scoped to clinician role or patient owner."""
    try:
        if current_user.role in {"admin", "practitioner", "practitioner_assigned"}:
            db_patients = db.query(HealthcarePatientModel).all()
        else:
            db_patients = (
                db.query(HealthcarePatientModel)
                .filter(HealthcarePatientModel.owner_user_id == current_user.id)
                .all()
            )
        if db_patients:
            return [
                {
                    "id": p.id,
                    "mrn": p.id,
                    "first_name": p.given_names[0] if p.given_names else "Synthetic",
                    "last_name": p.family_name,
                    "dob": p.birth_date,
                    "gender": p.gender,
                    "status": "active" if p.active else "inactive",
                    "phone": p.phone_masked,
                    "email": p.email,
                    "owner_user_id": p.owner_user_id,
                }
                for p in db_patients
            ]
    except Exception:
        pass

    return list(_PATIENT_STORE.values())


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(default="practitioner_assigned", alias="X-User-Role"),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Retrieves synthetic patient record with HIPAA-compliant masking.
    Supports defect simulation:
    - IDOR_PATIENT_RECORD_ACCESS: Permits access to unauthorized roles.
    """
    patient = _PATIENT_STORE.get(patient_id)
    db_patient = None
    try:
        db_patient = db.get(HealthcarePatientModel, patient_id)
    except Exception:
        pass

    if not patient and not db_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with MRN '{patient_id}' not found.",
        )

    is_idor_defect = x_simulate_defect == HealthcareDefectType.IDOR_PATIENT_RECORD_ACCESS.value

    # Role check
    if not is_idor_defect:
        effective_role = current_user.role if current_user.role != "passenger" else x_user_role
        if effective_role in ["unauthorized", "passenger", "guest"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Clinician not authorized for requested patient medical record.",
            )

        # IDOR tenant isolation check
        if db_patient and current_user.role not in {"admin", "practitioner", "practitioner_assigned"}:
            if db_patient.owner_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: IDOR protection prevented access to another patient's medical record.",
                )

    if patient:
        return patient

    return {
        "resourceType": "Patient",
        "id": db_patient.id,
        "active": db_patient.active,
        "name": [{"family": db_patient.family_name, "given": db_patient.given_names}],
        "gender": db_patient.gender,
        "birthDate": db_patient.birth_date,
        "owner_user_id": db_patient.owner_user_id,
    }


@router.get("/practitioners")
async def list_practitioners() -> List[Dict[str, Any]]:
    """Returns catalog of available clinical practitioners for scheduling."""
    return SYNTHETIC_PRACTITIONERS


@router.post("/observations", status_code=status.HTTP_201_CREATED)
async def record_observation(
    observation_data: Dict[str, Any],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Records and validates an HL7 FHIR Release 4 Observation (e.g. vital signs, labs).
    Persists to PostgreSQL with patient foreign key and tenant isolation.
    """
    obs_id = observation_data.get("id") or f"OBS-{len(_OBSERVATION_STORE) + 1:06d}"
    stored = dict(observation_data)
    stored["id"] = obs_id
    if "valueQuantity" in stored and isinstance(stored["valueQuantity"], dict):
        vq = dict(stored["valueQuantity"])
        if not vq.get("code"):
            vq["code"] = vq.get("unit", "")
        stored["valueQuantity"] = vq

    try:
        FHIRObservation.model_validate(stored)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"FHIR R4 Observation Contract Validation Failure: {exc}",
        )

    _OBSERVATION_STORE.append(stored)

    # Persistence to DB
    try:
        subj = observation_data.get("subject", {})
        patient_ref = subj.get("reference", "").replace("Patient/", "") if subj else ""
        if not patient_ref:
            patient_ref = observation_data.get("patient_id", "")

        # Ensure parent patient exists in DB for foreign key constraint
        if patient_ref and not db.get(HealthcarePatientModel, patient_ref):
            synth_parent = HealthcarePatientModel(
                id=patient_ref,
                owner_user_id=current_user.id,
                family_name="Patient",
                given_names=["Auto"],
                gender="unknown",
                birth_date="1990-01-01",
            )
            db.add(synth_parent)
            db.flush()

        coding = observation_data.get("code", {}).get("coding", [{}])[0]
        val_q = observation_data.get("valueQuantity", {})

        db_obs = HealthcareObservationModel(
            id=obs_id,
            patient_id=patient_ref,
            loinc_code=coding.get("code", "LOINC-UNK"),
            display_name=coding.get("display", "Clinical Observation"),
            value_quantity=float(val_q.get("value", 0.0)),
            unit=val_q.get("unit", ""),
            status=observation_data.get("status", "final"),
            effective_date_time=observation_data.get("effectiveDateTime", datetime.utcnow().isoformat()),
        )
        db.add(db_obs)
        db.commit()
    except Exception:
        db.rollback()

    return stored


@router.get("/observations")
async def list_observations(
    patient_id: Optional[str] = Query(default=None, description="Filter by Patient reference (e.g. MRN-HC-100000)"),
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists recorded clinical observations, optionally filtered by patient with tenant checks."""
    try:
        query = db.query(HealthcareObservationModel)
        if patient_id:
            target_id = patient_id.replace("Patient/", "")
            query = query.filter(HealthcareObservationModel.patient_id == target_id)
            if current_user.role not in {"admin", "practitioner", "practitioner_assigned"}:
                patient = db.get(HealthcarePatientModel, target_id)
                if patient and patient.owner_user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: IDOR protection prevented access to another patient's observations.",
                    )

        db_obs = query.all()
        if db_obs:
            return [
                {
                    "resourceType": "Observation",
                    "id": o.id,
                    "status": o.status,
                    "code": {"coding": [{"code": o.loinc_code, "display": o.display_name}]},
                    "subject": {"reference": f"Patient/{o.patient_id}"},
                    "effectiveDateTime": o.effective_date_time,
                    "valueQuantity": {"value": float(o.value_quantity) if o.value_quantity else 0.0, "unit": o.unit},
                }
                for o in db_obs
            ]
    except HTTPException:
        raise
    except Exception:
        pass

    if not patient_id:
        return _OBSERVATION_STORE

    target_ref = f"Patient/{patient_id}"
    return [
        obs for obs in _OBSERVATION_STORE
        if obs.get("subject", {}).get("reference") == target_ref
        or obs.get("subject", {}).get("reference") == patient_id
    ]


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def schedule_appointment(
    appointment_data: Dict[str, Any],
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> Dict[str, Any]:
    """
    Schedules an outpatient appointment with practitioner concurrency checks.
    Persists to PostgreSQL with tenant isolation.
    Supports defect simulation:
    - CONCURRENT_APPOINTMENT_DOUBLE_BOOKING: Bypasses calendar conflict check, permitting double booking.
    """
    appt_id = appointment_data.get("id") or f"APPT-HC-{len(_APPOINTMENT_STORE) + 1:06d}"
    stored = dict(appointment_data)
    stored["id"] = appt_id

    try:
        FHIRAppointment.model_validate(stored)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"FHIR R4 Appointment Contract Validation Failure: {exc}",
        )

    new_start = appointment_data.get("start")
    new_end = appointment_data.get("end")

    # Extract practitioner reference
    practitioner_ref = None
    for p in appointment_data.get("participant", []):
        actor_ref = p.get("actor", {}).get("reference", "")
        if "Practitioner" in actor_ref:
            practitioner_ref = actor_ref
            break

    is_double_booking_defect = x_simulate_defect in (
        HealthcareDefectType.CONCURRENT_APPOINTMENT_DOUBLE_BOOKING.value,
        "CONCURRENT_APPOINTMENT_DOUBLE_BOOKING",
        "DEF-HC-003",
        "DEF-HC-004",
    )

    # Concurrency verification: check for overlapping appointments for the same practitioner
    if not is_double_booking_defect and practitioner_ref and new_start and new_end:
        for existing in _APPOINTMENT_STORE:
            if existing.get("status") in ["cancelled", "entered-in-error"]:
                continue
            for ep in existing.get("participant", []):
                if ep.get("actor", {}).get("reference") == practitioner_ref:
                    if not (new_end <= existing["start"] or new_start >= existing["end"]):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Practitioner calendar conflict: Practitioner '{practitioner_ref}' "
                                f"is already booked between {existing['start']} and {existing['end']}."
                            ),
                        )
        try:
            db_clash = (
                db.query(HealthcareAppointmentModel)
                .filter(
                    HealthcareAppointmentModel.practitioner_ref == practitioner_ref,
                    HealthcareAppointmentModel.status != "cancelled",
                    HealthcareAppointmentModel.start_time < new_end,
                    HealthcareAppointmentModel.end_time > new_start,
                )
                .first()
            )
            if db_clash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Practitioner calendar conflict: Practitioner '{practitioner_ref}' "
                        f"is already booked between {db_clash.start_time} and {db_clash.end_time}."
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            pass

    appt_id = appointment_data.get("id") or f"APPT-HC-{len(_APPOINTMENT_STORE) + 1:06d}"
    stored = dict(appointment_data)
    stored["id"] = appt_id
    _APPOINTMENT_STORE.append(stored)

    # Persistence to DB
    try:
        patient_ref = None
        for p in appointment_data.get("participant", []):
            actor_ref = p.get("actor", {}).get("reference", "")
            if "Patient" in actor_ref:
                patient_ref = actor_ref.replace("Patient/", "")
                break
        if not patient_ref:
            patient_ref = f"MRN-HC-{current_user.id}"

        if not db.get(HealthcarePatientModel, patient_ref):
            db.add(
                HealthcarePatientModel(
                    id=patient_ref,
                    owner_user_id=current_user.id,
                    family_name="Patient",
                    given_names=["Auto"],
                    gender="unknown",
                    birth_date="1990-01-01",
                )
            )
            db.flush()

        db_appt = HealthcareAppointmentModel(
            id=appt_id,
            patient_id=patient_ref,
            practitioner_ref=practitioner_ref or "Practitioner/DR-CHEN-01",
            service_type="General Practice",
            start_time=new_start or datetime.utcnow().isoformat(),
            end_time=new_end or datetime.utcnow().isoformat(),
            status="booked",
        )
        db.add(db_appt)
        db.commit()
    except Exception:
        db.rollback()

    return stored


@router.get("/appointments")
async def list_appointments(
    current_user: User = Depends(get_current_domain_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists scheduled clinical appointments."""
    try:
        if current_user.role in {"admin", "practitioner", "practitioner_assigned"}:
            db_appts = db.query(HealthcareAppointmentModel).all()
        else:
            patient_ids = [
                p.id for p in db.query(HealthcarePatientModel).filter(HealthcarePatientModel.owner_user_id == current_user.id).all()
            ]
            db_appts = (
                db.query(HealthcareAppointmentModel)
                .filter(HealthcareAppointmentModel.patient_id.in_(patient_ids))
                .all()
            )
        if db_appts:
            return [
                {
                    "resourceType": "Appointment",
                    "id": a.id,
                    "status": a.status,
                    "start": a.start_time,
                    "end": a.end_time,
                    "participant": [
                        {"actor": {"reference": f"Patient/{a.patient_id}"}, "status": "accepted"},
                        {"actor": {"reference": a.practitioner_ref}, "status": "accepted"},
                    ],
                }
                for a in db_appts
            ]
    except Exception:
        pass

    return _APPOINTMENT_STORE


@router.post("/dosage/calculate", response_model=PediatricDosageResponse)
async def calculate_pediatric_dosage(
    request: PediatricDosageRequest,
    x_simulate_defect: Optional[str] = Header(default=None, alias="X-Simulate-Defect"),
) -> PediatricDosageResponse:
    """
    Calculates pediatric clinical medication dosage based on patient weight (kg).
    Supports defect simulation:
    - CLINICAL_DOSAGE_ROUNDING_ERROR: Injects arithmetic floor truncation defect.
    """
    is_rounding_defect = x_simulate_defect in (
        HealthcareDefectType.CLINICAL_DOSAGE_ROUNDING_ERROR.value,
        "CLINICAL_DOSAGE_ROUNDING_ERROR",
        "DEF-HC-004",
        "DEF-HC-003",
    )
    res = ClinicalDosageCalculator.calculate(
        weight_kg=request.patient_weight_kg,
        mg_per_kg=request.recommended_mg_per_kg,
        frequency_hours=request.frequency_hours,
        simulate_rounding_defect=is_rounding_defect,
    )
    warning = res.get("warning")
    if request.patient_weight_kg * request.recommended_mg_per_kg > 2000.0 or is_rounding_defect:
        warning = warning or "WARNING: Dose exceeds maximum safe pediatric threshold (exceeds max recommended limits)"

    return PediatricDosageResponse(
        patient_id=request.patient_id,
        drug_name=request.drug_name,
        patient_weight_kg=res["patient_weight_kg"],
        recommended_mg_per_kg=res["recommended_mg_per_kg"],
        single_dose_mg=res["single_dose_mg"],
        daily_total_mg=res["daily_total_mg"],
        frequency_hours=res["frequency_hours"],
        precision_verified=res["precision_verified"],
        warning=warning,
    )


@router.get("/defects")
async def list_healthcare_defects() -> List[Dict[str, Any]]:
    """Returns documentation and simulation instructions for Healthcare defect scenarios."""
    return [
        {
            "id": d.id,
            "name": d.name,
            "category": d.category,
            "affected_endpoint": d.affected_endpoint,
            "description": d.description,
            "how_to_reproduce": d.how_to_reproduce,
            "expected_qa_detection": d.expected_qa_detection,
            "headers": d.headers,
        }
        for d in HEALTHCARE_DEFECT_REGISTRY.values()
    ]
