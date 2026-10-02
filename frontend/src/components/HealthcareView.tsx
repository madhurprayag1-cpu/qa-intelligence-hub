import React, { useEffect, useState } from "react";
import {
  calculatePediatricDosage,
  createHealthcarePatient,
  fetchHealthcareAppointments,
  fetchHealthcareObservations,
  fetchHealthcarePatients,
  fetchHealthcarePractitioners,
  recordHealthcareObservation,
  scheduleHealthcareAppointment,
} from "../api";
import type {
  HealthcareAppointment,
  HealthcareObservation,
  HealthcarePatient,
  HealthcarePractitioner,
  PediatricDosageResponse,
} from "../types";

export function HealthcareView() {
  // State: Patient Intake
  const [patients, setPatients] = useState<HealthcarePatient[]>([]);
  const [activePatient, setActivePatient] = useState<HealthcarePatient | null>(null);
  const [firstName, setFirstName] = useState("Jane");
  const [lastName, setLastName] = useState("Doe");
  const [dob, setDob] = useState("1992-06-15");
  const [gender, setGender] = useState("female");
  const [phone, setPhone] = useState("+1-555-839-2001");
  const [email, setEmail] = useState("jane.doe@example.org");
  const [ssnRaw, setSsnRaw] = useState("123-45-6789");
  const [patientDefect, setPatientDefect] = useState<string>("");

  // State: Observations
  const [observations, setObservations] = useState<HealthcareObservation[]>([]);
  const [loincCode, setLoincCode] = useState("8867-4");
  const [obsDisplay, setObsDisplay] = useState("Heart rate");
  const [obsValue, setObsValue] = useState("72");
  const [obsUnit, setObsUnit] = useState("beats/min");

  // State: Appointments
  const [practitioners, setPractitioners] = useState<HealthcarePractitioner[]>([]);
  const [selectedPractitioner, setSelectedPractitioner] = useState<string>("");
  const [apptStart, setApptStart] = useState("2026-10-16T09:00:00Z");
  const [apptEnd, setApptEnd] = useState("2026-10-16T09:45:00Z");
  const [appointments, setAppointments] = useState<HealthcareAppointment[]>([]);
  const [apptDefect, setApptDefect] = useState<string>("");

  // State: Dosage Calculator
  const [dosageDrug, setDosageDrug] = useState("Amoxicillin");
  const [dosageWeight, setDosageWeight] = useState("15.5");
  const [dosageMgPerKg, setDosageMgPerKg] = useState("20");
  const [dosageFreq, setDosageFreq] = useState("8");
  const [dosageDefect, setDosageDefect] = useState<string>("");
  const [dosageResult, setDosageResult] = useState<PediatricDosageResponse | null>(null);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadObservations = async (patientId: string) => {
    try {
      const obs = await fetchHealthcareObservations(patientId);
      setObservations(obs);
    } catch {
      setObservations([]);
    }
  };

  // Load initial patients, practitioners, and appointments
  useEffect(() => {
    let isMounted = true;
    Promise.all([
      fetchHealthcarePatients().catch(() => []),
      fetchHealthcarePractitioners().catch(() => []),
      fetchHealthcareAppointments().catch(() => []),
    ]).then(([pts, prs, appts]) => {
      if (!isMounted) return;
      setPatients(pts);
      if (pts.length > 0) {
        setActivePatient(pts[0]);
        fetchHealthcareObservations(pts[0].id)
          .then((obs) => {
            if (isMounted) setObservations(obs);
          })
          .catch(() => {
            if (isMounted) setObservations([]);
          });
      }
      setPractitioners(prs);
      if (prs.length > 0) {
        setSelectedPractitioner(prs[0].id);
      }
      setAppointments(appts);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  // 1. Patient Intake Submission
  const handlePatientIntake = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const payload: Record<string, unknown> = {
        resourceType: "Patient",
        name: [{ family: lastName, given: [firstName] }],
        gender,
        birthDate: dob,
        telecom: [
          { system: "phone", value: phone },
          { system: "email", value: email },
        ],
        ssn_raw: ssnRaw,
      };

      const result = await createHealthcarePatient(
        payload,
        patientDefect ? patientDefect : undefined
      );

      setActivePatient(result);
      const updatedList = await fetchHealthcarePatients().catch(() => [result]);
      setPatients(updatedList);
      setSuccessMsg(
        `Patient ${firstName} ${lastName} enrolled successfully (MRN: ${result.id}). HIPAA de-identification applied.`
      );
      loadObservations(result.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Patient intake failed");
    } finally {
      setLoading(false);
    }
  };

  // 2. Record Observation
  const handleRecordObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activePatient) {
      setError("Please select or register a patient first.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const obsPayload = {
        resourceType: "Observation",
        status: "final",
        subject: { reference: `Patient/${activePatient.id}` },
        code: {
          coding: [{ code: loincCode, display: obsDisplay, system: "http://loinc.org" }],
        },
        effectiveDateTime: new Date().toISOString(),
        valueQuantity: {
          value: parseFloat(obsValue) || 0.0,
          unit: obsUnit,
        },
      };

      await recordHealthcareObservation(obsPayload);
      setSuccessMsg(`Clinical observation recorded for Patient ${activePatient.id} (${obsDisplay}: ${obsValue} ${obsUnit}).`);
      await loadObservations(activePatient.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Observation submission failed");
    } finally {
      setLoading(false);
    }
  };

  // Quick preset selector for LOINC
  const handleLoincPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "8867-4") {
      setLoincCode("8867-4");
      setObsDisplay("Heart rate");
      setObsValue("72");
      setObsUnit("beats/min");
    } else if (val === "8480-6") {
      setLoincCode("8480-6");
      setObsDisplay("Systolic blood pressure");
      setObsValue("120");
      setObsUnit("mmHg");
    } else if (val === "2339-0") {
      setLoincCode("2339-0");
      setObsDisplay("Blood glucose");
      setObsValue("95");
      setObsUnit("mg/dL");
    } else if (val === "29463-7") {
      setLoincCode("29463-7");
      setObsDisplay("Body weight");
      setObsValue("15.5");
      setObsUnit("kg");
    }
  };

  // 3. Schedule Appointment
  const handleScheduleAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activePatient) {
      setError("Please select or register a patient first.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const apptPayload = {
        resourceType: "Appointment",
        status: "booked",
        start: apptStart,
        end: apptEnd,
        participant: [
          { actor: { reference: `Patient/${activePatient.id}` }, status: "accepted" },
          { actor: { reference: selectedPractitioner || "Practitioner/DR-CHEN-01" }, status: "accepted" },
        ],
      };

      const res = await scheduleHealthcareAppointment(
        apptPayload,
        apptDefect ? apptDefect : undefined
      );

      if (apptDefect) {
        setSuccessMsg(`Appointment ${res.id} scheduled with simulated practitioner calendar conflict (double booking).`);
      } else {
        setSuccessMsg(`Appointment ${res.id} scheduled with ${selectedPractitioner}.`);
      }
      const appts = await fetchHealthcareAppointments().catch(() => [res]);
      setAppointments(appts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Appointment scheduling failed");
    } finally {
      setLoading(false);
    }
  };

  // 4. Calculate Pediatric Dosage
  const handleCalculateDosage = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const weight = parseFloat(dosageWeight);
      const mgKg = parseFloat(dosageMgPerKg);
      const freq = parseInt(dosageFreq, 10);

      if (isNaN(weight) || isNaN(mgKg) || isNaN(freq)) {
        throw new Error("Weight, mg/kg, and frequency must be valid numbers");
      }

      const res = await calculatePediatricDosage(
        {
          patient_id: activePatient ? activePatient.id : "MRN-HC-DEMO",
          drug_name: dosageDrug,
          patient_weight_kg: weight,
          recommended_mg_per_kg: mgKg,
          frequency_hours: freq,
        },
        dosageDefect ? dosageDefect : undefined
      );

      setDosageResult(res);
      setSuccessMsg(`Clinical dosage calculated for ${dosageDrug}: ${res.single_dose_mg} mg/dose.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Dosage calculation failed");
    } finally {
      setLoading(false);
    }
  };

  // Reset entire flow
  const handleResetFlow = () => {
    setFirstName("Jane");
    setLastName("Doe");
    setDob("1992-06-15");
    setSsnRaw("123-45-6789");
    setPhone("+1-555-839-2001");
    setEmail("jane.doe@example.org");
    setDosageResult(null);
    setError(null);
    setSuccessMsg(null);
    setPatientDefect("");
    setApptDefect("");
    setDosageDefect("");
  };

  return (
    <div className="domain-view healthcare-view" data-testid="healthcare-view">
      {/* Domain Header Banner */}
      <section className="domain-banner" data-testid="healthcare-banner">
        <div className="domain-banner-header">
          <div className="domain-badge-group">
            <span className="domain-pill" style={{ background: "rgba(16, 185, 129, 0.2)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.4)" }}>
              🏥 HEALTHCARE DOMAIN SUT
            </span>
            <span className="domain-standard-tag">HL7 FHIR R4 • HIPAA Safe Harbor • Clinical Precision</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleResetFlow}
            data-testid="healthcare-reset-btn"
          >
            🔄 Reset Workflow
          </button>
        </div>
        <p className="domain-desc">
          Execute realistic healthcare workflows: Patient Intake with HIPAA PHI de-identification,
          HL7 FHIR R4 Vital/Lab Observations, Outpatient Appointment scheduling with calendar conflict protection,
          and Pediatric Clinical Dosage calculations.
        </p>
      </section>

      {/* Global Alert Messages */}
      {error && (
        <div className="alert alert-danger fade-in" role="alert" data-testid="healthcare-error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && !error && (
        <div className="alert alert-success fade-in" role="alert" data-testid="healthcare-success-banner">
          <span>✅</span>
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Grid: 2 Columns */}
      <div className="domain-grid">
        {/* LEFT COLUMN: Patient Intake & HIPAA Masking */}
        <div className="domain-card-column">
          <section className="form-card" data-testid="patient-intake-card">
            <div className="card-header-styled">
              <span className="step-num">1</span>
              <div>
                <h3>Patient Intake & Safe Harbor De-Identification</h3>
                <p className="subtext">Ingest synthetic FHIR R4 Patient record and enforce Safe Harbor masking</p>
              </div>
            </div>

            {patients.length > 0 && (
              <div className="form-group mb-3">
                <label htmlFor="hc-switch-patient">Switch Active Enrolled Patient ({patients.length} available)</label>
                <select
                  id="hc-switch-patient"
                  value={activePatient?.id || ""}
                  onChange={(e) => {
                    const found = patients.find((p) => p.id === e.target.value);
                    if (found) {
                      setActivePatient(found);
                      loadObservations(found.id);
                    }
                  }}
                  data-testid="select-enrolled-patient"
                >
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} — {p.name && p.name[0] ? `${p.name[0].given.join(" ")} ${p.name[0].family}` : `${p.first_name || ""} ${p.last_name || ""}`}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <form onSubmit={handlePatientIntake} data-testid="patient-intake-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-first-name">First Given Name</label>
                  <input
                    id="hc-first-name"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    data-testid="input-patient-firstname"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-last-name">Family / Last Name</label>
                  <input
                    id="hc-last-name"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    data-testid="input-patient-lastname"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-dob">Date of Birth</label>
                  <input
                    id="hc-dob"
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    required
                    data-testid="input-patient-dob"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-gender">Gender Identity</label>
                  <select
                    id="hc-gender"
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    data-testid="select-patient-gender"
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="other">Other</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-phone">Contact Phone</label>
                  <input
                    id="hc-phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                    data-testid="input-patient-phone"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-ssn">Raw SSN (9 digits)</label>
                  <input
                    id="hc-ssn"
                    type="text"
                    value={ssnRaw}
                    onChange={(e) => setSsnRaw(e.target.value)}
                    placeholder="123-45-6789"
                    required
                    data-testid="input-patient-ssn"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="hc-email">Patient Email</label>
                <input
                  id="hc-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  data-testid="input-patient-email"
                />
              </div>

              {/* Defect Injection Hooks */}
              <div className="defect-hook-box">
                <label htmlFor="hc-patient-defect" className="defect-label">
                  🧪 QA Defect Injection Hook (Simulate Defect):
                </label>
                <select
                  id="hc-patient-defect"
                  value={patientDefect}
                  onChange={(e) => setPatientDefect(e.target.value)}
                  data-testid="select-patient-defect"
                >
                  <option value="">None (Standard HIPAA Safe Harbor)</option>
                  <option value="DEF-HC-001">
                    DEF-HC-001: PHI Exposure - Unmasked SSN Leak
                  </option>
                  <option value="PHI_EXPOSURE_UNMASKED_SSN">
                    PHI_EXPOSURE_UNMASKED_SSN (DEF-HC-001)
                  </option>
                  <option value="DEF-HC-005">
                    DEF-HC-005: FHIR Schema Validation Failure
                  </option>
                  <option value="FHIR_SCHEMA_VALIDATION_FAILURE">
                    FHIR_SCHEMA_VALIDATION_FAILURE (DEF-HC-005)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading}
                data-testid="submit-patient-btn"
              >
                {loading ? "Processing Intake..." : "🩺 Enrol Patient & Apply HIPAA Masking"}
              </button>
            </form>

            {/* Active Patient Safe Harbor Display Card */}
            {activePatient && (
              <div className="status-box mt-4" data-testid="active-patient-card">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online">
                    MRN: {activePatient.id}
                  </span>
                  <span
                    className={`status-pill ${activePatient.ssn_masked && activePatient.ssn_masked.includes("***") ? "status-pill-online" : "status-pill-offline"}`}
                    data-testid="hipaa-status-badge"
                  >
                    {activePatient.ssn_masked && activePatient.ssn_masked.includes("***")
                      ? "🛡️ SAFE HARBOR COMPLIANT"
                      : "🚨 PHI LEAK DETECTED"}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Patient Name:</span>
                    <strong data-testid="patient-name">
                      {activePatient.name && activePatient.name[0]
                        ? `${activePatient.name[0].given.join(" ")} ${activePatient.name[0].family}`
                        : `${activePatient.first_name || ""} ${activePatient.last_name || ""}`}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Date of Birth:</span>
                    <span>{activePatient.birthDate || activePatient.dob}</span>
                  </div>
                  <div>
                    <span className="meta-label">Masked SSN:</span>
                    <strong data-testid="patient-ssn-masked" style={{ color: activePatient.ssn_masked?.includes("***") ? "#38bdf8" : "#f43f5e" }}>
                      {activePatient.ssn_masked || "N/A"}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Masked Phone:</span>
                    <span data-testid="patient-phone-masked">
                      {activePatient.phone_masked || (activePatient.telecom && activePatient.telecom[0]?.value) || "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Clinical Vital Signs & Lab Observations */}
          <section className="form-card mt-4" data-testid="vital-observation-card">
            <div className="card-header-styled">
              <span className="step-num">2</span>
              <div>
                <h3>HL7 FHIR R4 Clinical Observations</h3>
                <p className="subtext">Log diagnostic vitals & lab results with LOINC codings</p>
              </div>
            </div>

            <form onSubmit={handleRecordObservation} data-testid="observation-form">
              <div className="form-group">
                <label htmlFor="hc-loinc-preset">Quick Observation Preset</label>
                <select
                  id="hc-loinc-preset"
                  onChange={handleLoincPreset}
                  data-testid="select-loinc-preset"
                >
                  <option value="8867-4">Heart Rate (8867-4 • beats/min)</option>
                  <option value="8480-6">Blood Pressure Systolic (8480-6 • mmHg)</option>
                  <option value="2339-0">Blood Glucose (2339-0 • mg/dL)</option>
                  <option value="29463-7">Body Weight (29463-7 • kg)</option>
                </select>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-loinc-code">LOINC Code</label>
                  <input
                    id="hc-loinc-code"
                    type="text"
                    value={loincCode}
                    onChange={(e) => setLoincCode(e.target.value)}
                    required
                    data-testid="input-loinc-code"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-obs-display">Clinical Display Name</label>
                  <input
                    id="hc-obs-display"
                    type="text"
                    value={obsDisplay}
                    onChange={(e) => setObsDisplay(e.target.value)}
                    required
                    data-testid="input-obs-display"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-obs-value">Measured Quantity Value</label>
                  <input
                    id="hc-obs-value"
                    type="number"
                    step="0.1"
                    value={obsValue}
                    onChange={(e) => setObsValue(e.target.value)}
                    required
                    data-testid="input-obs-value"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-obs-unit">Clinical Unit</label>
                  <input
                    id="hc-obs-unit"
                    type="text"
                    value={obsUnit}
                    onChange={(e) => setObsUnit(e.target.value)}
                    required
                    data-testid="input-obs-unit"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block"
                disabled={loading || !activePatient}
                data-testid="submit-observation-btn"
              >
                {loading ? "Recording..." : `📊 Log Observation for ${activePatient ? activePatient.id : "Patient"}`}
              </button>
            </form>

            {/* Observations List */}
            {observations.length > 0 && (
              <div className="mt-4" data-testid="observations-table-wrapper">
                <h4>Recorded FHIR Observations ({observations.length})</h4>
                <div className="table-responsive mt-2">
                  <table className="data-table" data-testid="observations-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>LOINC Code</th>
                        <th>Observation</th>
                        <th>Value</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {observations.map((obs, idx) => (
                        <tr key={obs.id || `obs-${idx}`}>
                          <td><code>{obs.id}</code></td>
                          <td><code>{obs.code.coding[0]?.code}</code></td>
                          <td>{obs.code.coding[0]?.display}</td>
                          <td><strong>{obs.valueQuantity?.value} {obs.valueQuantity?.unit}</strong></td>
                          <td><span className="status-badge badge-active">{obs.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN: Appointment Scheduling & Dosage Calculator */}
        <div className="domain-card-column">
          {/* Appointment Scheduling */}
          <section className="form-card" data-testid="appointment-scheduling-card">
            <div className="card-header-styled">
              <span className="step-num">3</span>
              <div>
                <h3>Outpatient Appointment Scheduling</h3>
                <p className="subtext">Book clinical visit with practitioner calendar concurrency locking</p>
              </div>
            </div>

            <form onSubmit={handleScheduleAppointment} data-testid="appointment-form">
              <div className="form-group">
                <label htmlFor="hc-practitioner">Select Practitioner</label>
                <select
                  id="hc-practitioner"
                  value={selectedPractitioner}
                  onChange={(e) => setSelectedPractitioner(e.target.value)}
                  data-testid="select-practitioner"
                >
                  {practitioners.map((pr) => (
                    <option key={pr.id} value={pr.id}>
                      {pr.name} ({pr.specialty})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-appt-start">Slot Start (ISO)</label>
                  <input
                    id="hc-appt-start"
                    type="text"
                    value={apptStart}
                    onChange={(e) => setApptStart(e.target.value)}
                    required
                    data-testid="input-appt-start"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-appt-end">Slot End (ISO)</label>
                  <input
                    id="hc-appt-end"
                    type="text"
                    value={apptEnd}
                    onChange={(e) => setApptEnd(e.target.value)}
                    required
                    data-testid="input-appt-end"
                  />
                </div>
              </div>

              {/* Defect injection hook for double booking */}
              <div className="defect-hook-box">
                <label htmlFor="hc-appt-defect" className="defect-label">
                  🧪 QA Concurrency Defect Hook:
                </label>
                <select
                  id="hc-appt-defect"
                  value={apptDefect}
                  onChange={(e) => setApptDefect(e.target.value)}
                  data-testid="select-appt-defect"
                >
                  <option value="">None (Enforce Calendar Locking)</option>
                  <option value="DEF-HC-003">
                    DEF-HC-003: Bypass Conflict Check (Simulate Double Booking)
                  </option>
                  <option value="DEF-HC-004">
                    DEF-HC-004: Bypass Conflict Check (Simulate Double Booking)
                  </option>
                  <option value="CONCURRENT_APPOINTMENT_DOUBLE_BOOKING">
                    CONCURRENT_APPOINTMENT_DOUBLE_BOOKING (DEF-HC-003)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading || !activePatient}
                data-testid="submit-appointment-btn"
              >
                {loading ? "Scheduling..." : "📅 Confirm Appointment"}
              </button>
            </form>

            {/* Scheduled Appointments Table */}
            {appointments.length > 0 && (
              <div className="mt-4" data-testid="appointments-list-wrapper">
                <h4>Scheduled Visits ({appointments.length})</h4>
                <div className="table-responsive mt-2">
                  <table className="data-table" data-testid="appointments-table">
                    <thead>
                      <tr>
                        <th>Appt ID</th>
                        <th>Practitioner</th>
                        <th>Start Time</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {appointments.map((a, idx) => (
                        <tr key={a.id || `appt-${idx}`}>
                          <td><code>{a.id}</code></td>
                          <td>
                            {a.participant?.find((p) => p.actor.reference.includes("Practitioner"))?.actor.reference.replace("Practitioner/", "") || "Clinician"}
                          </td>
                          <td>{a.start ? new Date(a.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "N/A"}</td>
                          <td><span className="status-badge badge-active">{a.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>

          {/* Pediatric Clinical Dosage Calculator */}
          <section className="form-card mt-4" data-testid="dosage-calculator-card">
            <div className="card-header-styled">
              <span className="step-num">4</span>
              <div>
                <h3>Pediatric Clinical Dosage Calculator</h3>
                <p className="subtext">Weight-based clinical pharmacology calculation engine</p>
              </div>
            </div>

            <form onSubmit={handleCalculateDosage} data-testid="dosage-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-drug-name">Medication / Drug</label>
                  <input
                    id="hc-drug-name"
                    type="text"
                    value={dosageDrug}
                    onChange={(e) => setDosageDrug(e.target.value)}
                    required
                    data-testid="input-dosage-drug"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-patient-weight">Patient Weight (kg)</label>
                  <input
                    id="hc-patient-weight"
                    type="number"
                    step="0.1"
                    value={dosageWeight}
                    onChange={(e) => setDosageWeight(e.target.value)}
                    required
                    data-testid="input-dosage-weight"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="hc-dosage-mgkg">Recommended mg/kg</label>
                  <input
                    id="hc-dosage-mgkg"
                    type="number"
                    step="0.5"
                    value={dosageMgPerKg}
                    onChange={(e) => setDosageMgPerKg(e.target.value)}
                    required
                    data-testid="input-dosage-mgkg"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="hc-dosage-freq">Dosing Frequency (hours)</label>
                  <select
                    id="hc-dosage-freq"
                    value={dosageFreq}
                    onChange={(e) => setDosageFreq(e.target.value)}
                    data-testid="select-dosage-freq"
                  >
                    <option value="6">Every 6 hours (4x/day)</option>
                    <option value="8">Every 8 hours (3x/day)</option>
                    <option value="12">Every 12 hours (2x/day)</option>
                    <option value="24">Every 24 hours (1x/day)</option>
                  </select>
                </div>
              </div>

              {/* Defect injection hook for dosage rounding error */}
              <div className="defect-hook-box">
                <label htmlFor="hc-dosage-defect" className="defect-label">
                  🧪 QA Arithmetic Defect Hook:
                </label>
                <select
                  id="hc-dosage-defect"
                  value={dosageDefect}
                  onChange={(e) => setDosageDefect(e.target.value)}
                  data-testid="select-dosage-defect"
                >
                  <option value="">None (Precision Decimal Verification)</option>
                  <option value="DEF-HC-004">
                    DEF-HC-004: Clinical Dosage Rounding Error (Truncation Defect)
                  </option>
                  <option value="DEF-HC-003">
                    DEF-HC-003: Clinical Dosage Arithmetic Error
                  </option>
                  <option value="CLINICAL_DOSAGE_ROUNDING_ERROR">
                    CLINICAL_DOSAGE_ROUNDING_ERROR (DEF-HC-004)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading}
                data-testid="submit-dosage-btn"
              >
                {loading ? "Calculating..." : "💊 Compute Clinical Dosage"}
              </button>
            </form>

            {/* Dosage Calculation Result */}
            {dosageResult && (
              <div className="status-box mt-4" data-testid="dosage-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online">
                    Rx: {dosageResult.drug_name}
                  </span>
                  <span
                    className={`status-pill ${dosageResult.precision_verified ? "status-pill-online" : "status-pill-offline"}`}
                    data-testid="dosage-precision-badge"
                  >
                    {dosageResult.precision_verified ? "✅ PRECISION VERIFIED" : "🚨 ROUNDING ERROR DETECTED"}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Single Dose:</span>
                    <strong data-testid="dosage-single-dose" style={{ fontSize: "16px", color: "#38bdf8" }}>
                      {dosageResult.single_dose_mg} mg
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Daily Total:</span>
                    <strong data-testid="dosage-daily-total" style={{ fontSize: "16px", color: "#10b981" }}>
                      {dosageResult.daily_total_mg} mg/day
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Interval:</span>
                    <span>Every {dosageResult.frequency_hours} hours</span>
                  </div>
                  <div>
                    <span className="meta-label">Patient Weight:</span>
                    <span>{dosageResult.patient_weight_kg} kg</span>
                  </div>
                </div>
                {dosageResult.warning && (
                  <div className="alert alert-warning mt-2" data-testid="dosage-warning-alert">
                    ⚠️ {dosageResult.warning}
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
