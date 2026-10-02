import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

/**
 * TelecomPage – Page Object for the Telecom (5G/BSS) domain view.
 * Wraps all stable data-testid selectors defined in TelecomView.tsx.
 */
export class TelecomPage extends BasePage {
  // Root view
  readonly view: Locator;
  readonly banner: Locator;

  // Feedback
  readonly errorBanner: Locator;
  readonly successBanner: Locator;

  // Plans
  readonly plansSection: Locator;
  readonly plansList: Locator;

  // Subscriber Provisioning
  readonly provisioningSection: Locator;
  readonly provisionForm: Locator;
  readonly inputMsisdn: Locator;
  readonly inputSubscriberBalance: Locator;
  readonly inputIccid: Locator;
  readonly inputImsi: Locator;
  readonly checkboxRoaming: Locator;
  readonly submitProvisionBtn: Locator;
  readonly activeSubscriberCard: Locator;
  readonly subscriberMsisdn: Locator;
  readonly subscriberStatus: Locator;
  readonly subscriberImsi: Locator;
  readonly subscriberBalance: Locator;
  readonly cpniLeakAlert: Locator;

  // CPNI & Lifecycle
  readonly cpniLifecycleSection: Locator;
  readonly selectSubStatus: Locator;
  readonly selectLifecycleDefect: Locator;
  readonly submitTransitionBtn: Locator;
  readonly inspectCpniBtn: Locator;
  readonly selectCpniDefect: Locator;

  // SIM Swap
  readonly simSwapSection: Locator;
  readonly simSwapForm: Locator;
  readonly inputSwapMsisdn: Locator;
  readonly inputSwapIccid: Locator;
  readonly inputSwapImsi: Locator;
  readonly selectSwapDefect: Locator;
  readonly submitSwapBtn: Locator;
  readonly swapResultBox: Locator;
  readonly simSwapStatus: Locator;

  // CDR Rating
  readonly cdrRatingSection: Locator;
  readonly cdrRatingForm: Locator;
  readonly selectCdrType: Locator;
  readonly selectCdrZone: Locator;
  readonly inputCdrDestination: Locator;
  readonly inputCdrBytes: Locator;
  readonly inputCdrDuration: Locator;
  readonly selectCdrDefect: Locator;
  readonly submitCdrBtn: Locator;
  readonly cdrResultBox: Locator;
  readonly cdrId: Locator;
  readonly cdrRatedAmount: Locator;
  readonly cdrRemainingBalance: Locator;

  constructor(page: Page) {
    super(page);

    // Root
    this.view = this.byTestId("telecom-view");
    this.banner = this.byTestId("telecom-banner");

    // Feedback
    this.errorBanner = this.byTestId("telecom-error-banner");
    this.successBanner = this.byTestId("telecom-success-banner");

    // Plans
    this.plansSection = this.byTestId("plans-section");
    this.plansList = this.byTestId("plans-list");

    // Subscriber Provisioning
    this.provisioningSection = this.byTestId("provisioning-section");
    this.provisionForm = this.byTestId("provision-form");
    this.inputMsisdn = this.byTestId("input-msisdn");
    this.inputSubscriberBalance = this.byTestId("input-subscriber-balance");
    this.inputIccid = this.byTestId("input-iccid");
    this.inputImsi = this.byTestId("input-imsi");
    this.checkboxRoaming = this.byTestId("checkbox-roaming");
    this.submitProvisionBtn = this.byTestId("submit-provision-btn");
    this.activeSubscriberCard = this.byTestId("active-subscriber-card");
    this.subscriberMsisdn = this.byTestId("subscriber-msisdn");
    this.subscriberStatus = this.byTestId("subscriber-status");
    this.subscriberImsi = this.byTestId("subscriber-imsi");
    this.subscriberBalance = this.byTestId("subscriber-balance");
    this.cpniLeakAlert = this.byTestId("cpni-leak-alert");

    // CPNI & Lifecycle
    this.cpniLifecycleSection = this.byTestId("cpni-lifecycle-section");
    this.selectSubStatus = this.byTestId("select-sub-status");
    this.selectLifecycleDefect = this.byTestId("select-lifecycle-defect");
    this.submitTransitionBtn = this.byTestId("submit-transition-btn");
    this.inspectCpniBtn = this.byTestId("inspect-cpni-btn");
    this.selectCpniDefect = this.byTestId("select-cpni-defect");

    // SIM Swap
    this.simSwapSection = this.byTestId("sim-swap-section");
    this.simSwapForm = this.byTestId("sim-swap-form");
    this.inputSwapMsisdn = this.byTestId("input-swap-msisdn");
    this.inputSwapIccid = this.byTestId("input-swap-iccid");
    this.inputSwapImsi = this.byTestId("input-swap-imsi");
    this.selectSwapDefect = this.byTestId("select-swap-defect");
    this.submitSwapBtn = this.byTestId("submit-swap-btn");
    this.swapResultBox = this.byTestId("swap-result-box");
    this.simSwapStatus = this.byTestId("sim-swap-status");

    // CDR Rating
    this.cdrRatingSection = this.byTestId("cdr-rating-section");
    this.cdrRatingForm = this.byTestId("cdr-rating-form");
    this.selectCdrType = this.byTestId("select-cdr-type");
    this.selectCdrZone = this.byTestId("select-cdr-zone");
    this.inputCdrDestination = this.byTestId("input-cdr-destination");
    this.inputCdrBytes = this.byTestId("input-cdr-bytes");
    this.inputCdrDuration = this.byTestId("input-cdr-duration");
    this.selectCdrDefect = this.byTestId("select-cdr-defect");
    this.submitCdrBtn = this.byTestId("submit-cdr-btn");
    this.cdrResultBox = this.byTestId("cdr-result-box");
    this.cdrId = this.byTestId("cdr-id");
    this.cdrRatedAmount = this.byTestId("cdr-rated-amount");
    this.cdrRemainingBalance = this.byTestId("cdr-remaining-balance");
  }

  /** Navigate to root, authenticate with demo credentials, then switch to Telecom domain. */
  async goto() {
    await this.page.goto("/");
    const healthPill = this.page.locator('[data-testid="health-status-pill"]');
    await expect(healthPill).toBeVisible({ timeout: 15000 });
    await expect(healthPill).toContainText(/Backend: HEALTHY/i);

    const loginForm = this.page.locator('[data-testid="demo-login-form"]');
    if (await loginForm.isVisible().catch(() => false)) {
      await this.page.locator('input[aria-label="Demo email"]').fill("passenger@qahub.io");
      await this.page.locator('input[aria-label="Demo password"]').fill("passenger123");
      await this.page.locator('[data-testid="login-btn"]').click();
      await expect(this.page.locator('[data-testid="auth-status"]')).toBeVisible({ timeout: 6000 });
    }

    await this.selectTelecomDomain();
  }

  /** Click the Telecom domain tab. */
  async selectTelecomDomain() {
    const domainBtn = this.byTestId("domain-select-telecom");
    await expect(domainBtn).toBeVisible({ timeout: 8000 });
    await domainBtn.click();
    await expect(this.view).toBeVisible({ timeout: 8000 });
  }

  /** Get plan card by plan_id. */
  planCard(planId: string): Locator {
    return this.byTestId(`plan-card-${planId}`);
  }

  /**
   * Provision a new subscriber line.
   * Waits for the active-subscriber-card to appear as confirmation.
   */
  async provisionSubscriber(opts: {
    msisdn: string;
    iccid?: string;
    imsi?: string;
    balance?: string;
  }) {
    await this.inputMsisdn.fill(opts.msisdn);
    if (opts.iccid) await this.inputIccid.fill(opts.iccid);
    if (opts.imsi) await this.inputImsi.fill(opts.imsi);
    if (opts.balance) await this.inputSubscriberBalance.fill(opts.balance);
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes("/telecom/subscribers") && response.request().method() === "POST"
    );
    await this.submitProvisionBtn.click();
    const response = await responsePromise;
    if (!response.ok()) {
      throw new Error(`Subscriber API ${response.status()}: ${await response.text()}`);
    }
    await expect(this.activeSubscriberCard).toBeVisible({ timeout: 15000 });
  }

  /** Perform a SIM swap, waits for the swap result box. */
  async simSwap(opts: {
    msisdn: string;
    newIccid: string;
    newImsi?: string;
    defect?: string;
  }) {
    await this.inputSwapMsisdn.fill(opts.msisdn);
    await this.inputSwapIccid.fill(opts.newIccid);
    if (opts.newImsi) await this.inputSwapImsi.fill(opts.newImsi);
    if (opts.defect) {
      await this.selectSwapDefect.selectOption(opts.defect).catch(async () => {
        const option = this.selectSwapDefect.locator(`option[value*="${opts.defect}"]`);
        if (await option.count()) {
          const val = await option.getAttribute("value");
          if (val) await this.selectSwapDefect.selectOption(val);
        }
      });
    }
    await this.submitSwapBtn.click();
    await expect(this.swapResultBox).toBeVisible({ timeout: 15000 });
  }

  /** Rate a CDR and wait for the result box. */
  async rateCDR(opts: {
    callType?: string;
    zone?: string;
    destination?: string;
    bytes?: string;
    durationSec?: string;
    defect?: string;
  }) {
    if (opts.callType) await this.selectCdrType.selectOption(opts.callType);
    if (opts.zone) await this.selectCdrZone.selectOption(opts.zone);
    if (opts.destination) await this.inputCdrDestination.fill(opts.destination);
    if (opts.callType === "DATA" && opts.bytes) await this.inputCdrBytes.fill(opts.bytes);
    if (opts.callType !== "DATA" && opts.durationSec) await this.inputCdrDuration.fill(opts.durationSec);
    if (opts.defect) {
      await this.selectCdrDefect.selectOption(opts.defect).catch(async () => {
        const option = this.selectCdrDefect.locator(`option[value*="${opts.defect}"]`);
        if (await option.count()) {
          const val = await option.getAttribute("value");
          if (val) await this.selectCdrDefect.selectOption(val);
        }
      });
    }
    await this.submitCdrBtn.click();
    await expect(this.cdrResultBox).toBeVisible({ timeout: 15000 });
  }
}
