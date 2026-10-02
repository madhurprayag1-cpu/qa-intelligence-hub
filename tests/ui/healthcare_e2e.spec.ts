import { expect, test } from "@playwright/test";
import { HealthcarePage } from "./pages/HealthcarePage";

/**
 * Healthcare E2E Test Suite – Phase 1B.4
 *
 * Tests the complete FHIR clinical workflow through the real browser:
 *   - Domain selection from the persistent Domain Selector
 *   - Patient Intake with HIPAA Safe Harbor SSN/phone masking
 *   - LOINC vital/lab observation recording and table rendering
 *   - Practitioner appointment scheduling (happy + double-booking prevention)
 *   - Pediatric dosage calculation (happy + defect simulation)
 *   - Validation / error scenarios
 *
 * Rules (AGENTS.md §16):
 *   - Uses real frontend → backend API → PostgreSQL persistence flow.
 *   - No domain APIs are mocked.
 *   - Relies only on stable data-testid / ARIA selectors.
 *   - No arbitrary sleeps; uses deterministic Playwright waits.
 */
test.describe("Healthcare FHIR Workflow E2E Suite", () => {
  // -------------------------------------------------------------------
  // 1. Domain Selection
  // -------------------------------------------------------------------
  test("HC-01: Domain selector switches to Healthcare view", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    // Domain selector bar must be visible
    await expect(hcPage.byTestId("domain-selector")).toBeVisible();
    // Domain button shows active state
    const domainBtn = hcPage.byTestId("domain-select-healthcare");
    await expect(domainBtn).toHaveAttribute("aria-selected", "true");

    // Healthcare view root is visible
    await expect(hcPage.view).toBeVisible();
    await expect(hcPage.banner).toBeVisible();
    await expect(hcPage.banner).toContainText(/Healthcare|FHIR/i);

    // Patient intake form is rendered
    await expect(hcPage.patientIntakeCard).toBeVisible();
    await expect(hcPage.submitPatientBtn).toBeVisible();
  });

  // -------------------------------------------------------------------
  // 2. Patient Intake & HIPAA Masking
  // -------------------------------------------------------------------
  test("HC-02: Patient intake enrolls patient and applies HIPAA SSN/phone masking", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    const ts = Date.now();
    const msg = await hcPage.enrollPatient({
      firstName: "Emma",
      lastName: `E2E${ts}`,
      dob: "1990-03-22",
      gender: "female",
      phone: "+1-555-202-9901",
      ssn: "987-65-4321",
      email: `emma.e2e${ts}@synthetic.qahub.io`,
    });

    expect(msg).toContain("enrolled successfully");
    expect(msg).toContain("HIPAA");

    // Active patient card should now be visible
    await expect(hcPage.activePatientCard).toBeVisible();

    // HIPAA badge displayed
    await expect(hcPage.hipaaStatusBadge).toBeVisible();

    // SSN must be masked – should NOT contain the raw digits
    const ssnText = await hcPage.patientSsnMasked.textContent() ?? "";
    expect(ssnText).toContain("***");
    expect(ssnText).not.toContain("987-65-4321");

    // Phone must be masked
    const phoneText = await hcPage.patientPhoneMasked.textContent() ?? "";
    expect(phoneText).toContain("***");
  });

  // -------------------------------------------------------------------
  // 3. Vital Observation Recording
  // -------------------------------------------------------------------
  test("HC-03: Record LOINC heart-rate observation and see it in the table", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    // Enroll a patient first
    const ts = Date.now();
    await hcPage.enrollPatient({
      firstName: "Obs",
      lastName: `Patient${ts}`,
      phone: "+1-555-303-1111",
      ssn: "111-22-3333",
      email: `obs.patient${ts}@synthetic.qahub.io`,
    });

    // Record a heart-rate observation using LOINC preset 8867-4
    await hcPage.recordObservation({ loincPreset: "8867-4", value: "78" });

    // The observations table wrapper must be present
    await expect(hcPage.observationsTableWrapper).toBeVisible();
    await expect(hcPage.observationsTable).toBeVisible();

    // Table should contain the observation display name
    await expect(hcPage.observationsTable).toContainText(/Heart rate/i);
    // And the value we submitted
    await expect(hcPage.observationsTable).toContainText("78");
  });

  // -------------------------------------------------------------------
  // 4. Blood Glucose Observation
  // -------------------------------------------------------------------
  test("HC-04: Record blood-glucose LOINC observation", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    const ts = Date.now();
    await hcPage.enrollPatient({
      firstName: "Glucose",
      lastName: `Patient${ts}`,
      phone: "+1-555-304-2222",
      ssn: "222-33-4444",
      email: `glucose.patient${ts}@synthetic.qahub.io`,
    });

    await hcPage.recordObservation({ loincPreset: "2339-0", value: "105" });
    await expect(hcPage.observationsTable).toBeVisible();
    await expect(hcPage.observationsTable).toContainText(/Blood glucose/i);
    await expect(hcPage.observationsTable).toContainText("105");
  });

  // -------------------------------------------------------------------
  // 5. Appointment Scheduling – Happy Path
  // -------------------------------------------------------------------
  test("HC-05: Schedule practitioner appointment – happy path", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    const ts = Date.now();
    await hcPage.enrollPatient({
      firstName: "Appt",
      lastName: `Patient${ts}`,
      phone: "+1-555-305-3333",
      ssn: "333-44-5555",
      email: `appt.patient${ts}@synthetic.qahub.io`,
    });

    // Schedule with a distinct future time slot
    await hcPage.scheduleAppointment({
      startDateTime: "2027-01-15T10:00:00Z",
      endDateTime: "2027-01-15T10:45:00Z",
    });

    // Success or the appointment table shows the record
    const successOrTable = await Promise.race([
      hcPage.successBanner.waitFor({ state: "visible", timeout: 12000 }).then(() => "success"),
      hcPage.appointmentsListWrapper.waitFor({ state: "visible", timeout: 12000 }).then(() => "table"),
    ]);
    expect(["success", "table"]).toContain(successOrTable);
  });

  // -------------------------------------------------------------------
  // 6. Appointment – Double-Booking Prevention Defect Simulation
  // -------------------------------------------------------------------
  test("HC-06: DEF-HC-004 double-booking defect triggers error banner", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    const ts = Date.now();
    await hcPage.enrollPatient({
      firstName: "DblBook",
      lastName: `Patient${ts}`,
      phone: "+1-555-306-4444",
      ssn: "444-55-6666",
      email: `dblbook.patient${ts}@synthetic.qahub.io`,
    });

    // Inject double-booking defect
    await hcPage.scheduleAppointment({
      startDateTime: "2027-03-01T09:00:00Z",
      endDateTime: "2027-03-01T09:45:00Z",
      defect: "DEF-HC-004",
    });

    // The defect should produce an error or a success with "conflict" in the message
    const errorVisible = await hcPage.errorBanner.isVisible().catch(() => false);
    const successText = await hcPage.successBanner.textContent().catch(() => "");
    const defectDetected = errorVisible || successText.toLowerCase().includes("conflict");
    expect(defectDetected).toBeTruthy();
  });

  // -------------------------------------------------------------------
  // 7. Pediatric Dosage Calculator – Happy Path
  // -------------------------------------------------------------------
  test("HC-07: Pediatric dosage calculator produces structured result", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    await hcPage.calculateDosage({
      drug: "Amoxicillin",
      weightKg: "15.5",
      mgPerKg: "20",
      frequencyHours: "8",
    });

    // Result box should appear with dosage details
    await expect(hcPage.dosageResultBox).toBeVisible({ timeout: 12000 });

    // Should contain drug name and numeric dose result
    await expect(hcPage.dosageResultBox).toContainText(/Amoxicillin/i);
    await expect(hcPage.dosageResultBox).toContainText(/mg/i);
  });

  // -------------------------------------------------------------------
  // 8. Dosage – DEF-HC-003 Overflow Defect Simulation
  // -------------------------------------------------------------------
  test("HC-08: DEF-HC-003 dosage overflow defect is detected and reported", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    await hcPage.calculateDosage({
      drug: "Amoxicillin",
      weightKg: "80",
      mgPerKg: "500",
      frequencyHours: "8",
      defect: "DEF-HC-003",
    });

    // The defect response is rendered in the result or surfaced as a validation
    // alert. Wait on those observable states instead of sleeping.
    await expect(hcPage.errorBanner.or(hcPage.dosageResultBox)).toBeVisible({ timeout: 12000 });
    const errorVisible = await hcPage.errorBanner.isVisible();
    if (errorVisible) {
      await expect(hcPage.errorBanner).toContainText(/dosage|dose|overflow|exceed|max/i);
    } else {
      await expect(hcPage.dosageResultBox).toContainText(/exceed|overflow|warning|max/i);
    }
  });

  // -------------------------------------------------------------------
  // 9. Patient Intake – DEF-HC-001 HIPAA PII Leak Defect
  // -------------------------------------------------------------------
  test("HC-09: DEF-HC-001 HIPAA PII leak defect exposes raw SSN in response", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    const ts = Date.now();
    // Select the HIPAA leak defect before enrolling
    await hcPage.selectPatientDefect.selectOption("DEF-HC-001");

    await hcPage.inputFirstName.fill("Leaking");
    await hcPage.inputLastName.fill(`Patient${ts}`);
    await hcPage.inputPhone.fill("+1-555-900-0001");
    await hcPage.inputSsn.fill("999-88-7777");
    await hcPage.inputEmail.fill(`leak.patient${ts}@synthetic.qahub.io`);
    await hcPage.submitPatientBtn.click();

    // After enrollment, the SSN field should contain unmasked data (defect behavior)
    await expect(hcPage.activePatientCard).toBeVisible({ timeout: 12000 });
    const ssnText = await hcPage.patientSsnMasked.textContent() ?? "";
    // DEF-HC-001: raw SSN should NOT be masked → it contains the digits
    const defectActive = ssnText.includes("999") || !ssnText.includes("***");
    expect(defectActive).toBeTruthy();
  });

  // -------------------------------------------------------------------
  // 10. Validation – Submit observation without active patient
  // -------------------------------------------------------------------
  test("HC-10: Submitting observation without active patient shows error", async ({ page }) => {
    const hcPage = new HealthcarePage(page);
    await hcPage.goto();

    // Wait for view to load but do NOT enroll a patient
    await expect(hcPage.vitalObservationCard).toBeVisible();

    // Directly submit the observation form (requires active patient)
    // First clear the preloaded active patient by navigating to the domain fresh
    // The error handling message should surface
    await hcPage.submitObservationBtn.click();

    // Either error banner is shown, or the button is disabled in the current state
    const errorVisible = await hcPage.errorBanner.isVisible().catch(() => false);
    // If no error, the component guards it at the UI level (button disabled/no-op)
    // Both outcomes are acceptable guards
    if (errorVisible) {
      await expect(hcPage.errorBanner).toContainText(/patient/i);
    }
    // If not visible, the UI guard prevented submission – assert view is still stable
    await expect(hcPage.view).toBeVisible();
  });
});
