import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

/**
 * HealthcarePage – Page Object for the Healthcare (FHIR) domain view.
 * Wraps all stable data-testid selectors defined in HealthcareView.tsx.
 * Inherits navigation, resilient waits, and self-healing engine from BasePage.
 */
export class HealthcarePage extends BasePage {
  // Root view
  readonly view: Locator;
  readonly banner: Locator;

  // Feedback
  readonly errorBanner: Locator;
  readonly successBanner: Locator;

  // Patient Intake
  readonly patientIntakeCard: Locator;
  readonly patientIntakeForm: Locator;
  readonly inputFirstName: Locator;
  readonly inputLastName: Locator;
  readonly inputDob: Locator;
  readonly selectGender: Locator;
  readonly inputPhone: Locator;
  readonly inputSsn: Locator;
  readonly inputEmail: Locator;
  readonly selectPatientDefect: Locator;
  readonly submitPatientBtn: Locator;
  readonly activePatientCard: Locator;
  readonly hipaaStatusBadge: Locator;
  readonly patientName: Locator;
  readonly patientSsnMasked: Locator;
  readonly patientPhoneMasked: Locator;

  // Observations
  readonly vitalObservationCard: Locator;
  readonly observationForm: Locator;
  readonly selectLoincPreset: Locator;
  readonly inputLoincCode: Locator;
  readonly inputObsDisplay: Locator;
  readonly inputObsValue: Locator;
  readonly inputObsUnit: Locator;
  readonly submitObservationBtn: Locator;
  readonly observationsTable: Locator;
  readonly observationsTableWrapper: Locator;

  // Appointments
  readonly appointmentCard: Locator;
  readonly appointmentForm: Locator;
  readonly selectPractitioner: Locator;
  readonly inputApptStart: Locator;
  readonly inputApptEnd: Locator;
  readonly selectApptDefect: Locator;
  readonly submitAppointmentBtn: Locator;
  readonly appointmentsTable: Locator;
  readonly appointmentsListWrapper: Locator;

  // Dosage Calculator
  readonly dosageCalculatorCard: Locator;
  readonly dosageForm: Locator;
  readonly inputDosageDrug: Locator;
  readonly inputDosageWeight: Locator;
  readonly inputDosageMgKg: Locator;
  readonly selectDosageFreq: Locator;
  readonly selectDosageDefect: Locator;
  readonly submitDosageBtn: Locator;
  readonly dosageResultBox: Locator;

  constructor(page: Page) {
    super(page);

    // Root
    this.view = this.byTestId("healthcare-view");
    this.banner = this.byTestId("healthcare-banner");

    // Feedback
    this.errorBanner = this.byTestId("healthcare-error-banner");
    this.successBanner = this.byTestId("healthcare-success-banner");

    // Patient Intake
    this.patientIntakeCard = this.byTestId("patient-intake-card");
    this.patientIntakeForm = this.byTestId("patient-intake-form");
    this.inputFirstName = this.byTestId("input-patient-firstname");
    this.inputLastName = this.byTestId("input-patient-lastname");
    this.inputDob = this.byTestId("input-patient-dob");
    this.selectGender = this.byTestId("select-patient-gender");
    this.inputPhone = this.byTestId("input-patient-phone");
    this.inputSsn = this.byTestId("input-patient-ssn");
    this.inputEmail = this.byTestId("input-patient-email");
    this.selectPatientDefect = this.byTestId("select-patient-defect");
    this.submitPatientBtn = this.byTestId("submit-patient-btn");
    this.activePatientCard = this.byTestId("active-patient-card");
    this.hipaaStatusBadge = this.byTestId("hipaa-status-badge");
    this.patientName = this.byTestId("patient-name");
    this.patientSsnMasked = this.byTestId("patient-ssn-masked");
    this.patientPhoneMasked = this.byTestId("patient-phone-masked");

    // Observations
    this.vitalObservationCard = this.byTestId("vital-observation-card");
    this.observationForm = this.byTestId("observation-form");
    this.selectLoincPreset = this.byTestId("select-loinc-preset");
    this.inputLoincCode = this.byTestId("input-loinc-code");
    this.inputObsDisplay = this.byTestId("input-obs-display");
    this.inputObsValue = this.byTestId("input-obs-value");
    this.inputObsUnit = this.byTestId("input-obs-unit");
    this.submitObservationBtn = this.byTestId("submit-observation-btn");
    this.observationsTable = this.byTestId("observations-table");
    this.observationsTableWrapper = this.byTestId("observations-table-wrapper");

    // Appointments
    this.appointmentCard = this.byTestId("appointment-scheduling-card");
    this.appointmentForm = this.byTestId("appointment-form");
    this.selectPractitioner = this.byTestId("select-practitioner");
    this.inputApptStart = this.byTestId("input-appt-start");
    this.inputApptEnd = this.byTestId("input-appt-end");
    this.selectApptDefect = this.byTestId("select-appt-defect");
    this.submitAppointmentBtn = this.byTestId("submit-appointment-btn");
    this.appointmentsTable = this.byTestId("appointments-table");
    this.appointmentsListWrapper = this.byTestId("appointments-list-wrapper");

    // Dosage
    this.dosageCalculatorCard = this.byTestId("dosage-calculator-card");
    this.dosageForm = this.byTestId("dosage-form");
    this.inputDosageDrug = this.byTestId("input-dosage-drug");
    this.inputDosageWeight = this.byTestId("input-dosage-weight");
    this.inputDosageMgKg = this.byTestId("input-dosage-mgkg");
    this.selectDosageFreq = this.byTestId("select-dosage-freq");
    this.selectDosageDefect = this.byTestId("select-dosage-defect");
    this.submitDosageBtn = this.byTestId("submit-dosage-btn");
    this.dosageResultBox = this.byTestId("dosage-result-box");
  }

  /** Navigate to the app root, sign in with demo credentials, then switch to Healthcare domain. */
  async goto() {
    await this.page.goto("/");
    const healthPill = this.page.locator('[data-testid="health-status-pill"]');
    await expect(healthPill).toBeVisible({ timeout: 15000 });
    await expect(healthPill).toContainText(/Backend: HEALTHY/i);

    // Sign in if the login form is visible
    const loginForm = this.page.locator('[data-testid="demo-login-form"]');
    if (await loginForm.isVisible().catch(() => false)) {
      await this.page.locator('input[aria-label="Demo email"]').fill("passenger@qahub.io");
      await this.page.locator('input[aria-label="Demo password"]').fill("passenger123");
      await this.page.locator('[data-testid="login-btn"]').click();
      await expect(this.page.locator('[data-testid="auth-status"]')).toBeVisible({ timeout: 6000 });
    }

    // Switch domain
    await this.selectHealthcareDomain();
  }

  /** Click the Healthcare domain tab in the persistent domain selector bar. */
  async selectHealthcareDomain() {
    const domainBtn = this.byTestId("domain-select-healthcare");
    await expect(domainBtn).toBeVisible({ timeout: 8000 });
    await domainBtn.click();
    await expect(this.view).toBeVisible({ timeout: 8000 });
  }

  /**
   * Enroll a new patient through the Patient Intake form.
   * Returns the success message text.
   */
  async enrollPatient(opts: {
    firstName: string;
    lastName: string;
    dob?: string;
    phone?: string;
    email?: string;
    ssn?: string;
    gender?: string;
  }) {
    await this.inputFirstName.fill(opts.firstName);
    await this.inputLastName.fill(opts.lastName);
    if (opts.dob) await this.inputDob.fill(opts.dob);
    if (opts.gender) await this.selectGender.selectOption(opts.gender);
    if (opts.phone) await this.inputPhone.fill(opts.phone);
    if (opts.ssn) await this.inputSsn.fill(opts.ssn);
    if (opts.email) await this.inputEmail.fill(opts.email);
    await this.submitPatientBtn.click();
    await expect(this.successBanner).toBeVisible({ timeout: 12000 });
    return (await this.successBanner.textContent()) ?? "";
  }

  /** Record a clinical LOINC observation for the active patient. */
  async recordObservation(opts: {
    loincPreset: string;
    value?: string;
  }) {
    await this.selectLoincPreset.selectOption(opts.loincPreset);
    if (opts.value) {
      await this.inputObsValue.fill(opts.value);
    }
    await this.submitObservationBtn.click();
    await expect(this.successBanner).toBeVisible({ timeout: 12000 });
  }

  /** Schedule an appointment for the active patient. */
  async scheduleAppointment(opts?: {
    startDateTime?: string;
    endDateTime?: string;
    defect?: string;
  }) {
    if (opts?.startDateTime) await this.inputApptStart.fill(opts.startDateTime);
    if (opts?.endDateTime) await this.inputApptEnd.fill(opts.endDateTime);
    if (opts?.defect) {
      await this.selectApptDefect.selectOption(opts.defect).catch(() => {});
    }
    await this.submitAppointmentBtn.click();
  }

  /** Calculate pediatric dosage. */
  async calculateDosage(opts: {
    drug?: string;
    weightKg?: string;
    mgPerKg?: string;
    frequencyHours?: string;
    defect?: string;
  }) {
    if (opts.drug) await this.inputDosageDrug.fill(opts.drug);
    if (opts.weightKg) await this.inputDosageWeight.fill(opts.weightKg);
    if (opts.mgPerKg) await this.inputDosageMgKg.fill(opts.mgPerKg);
    if (opts.frequencyHours) await this.selectDosageFreq.selectOption(opts.frequencyHours);
    if (opts.defect) {
      await this.selectDosageDefect.selectOption(opts.defect).catch(() => {});
    }
    await this.submitDosageBtn.click();
  }
}
