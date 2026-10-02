import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

/**
 * FinTechPage – Page Object for the FinTech (Core Banking / Ledger) domain view.
 * Wraps all stable data-testid selectors defined in FinTechView.tsx.
 */
export class FinTechPage extends BasePage {
  // Root view
  readonly view: Locator;
  readonly banner: Locator;

  // Feedback
  readonly errorBanner: Locator;
  readonly successBanner: Locator;

  // KYC
  readonly kycOnboardingCard: Locator;
  readonly kycForm: Locator;
  readonly inputKycCustomerId: Locator;
  readonly inputKycName: Locator;
  readonly inputKycIncome: Locator;
  readonly inputKycDob: Locator;
  readonly inputKycDoc: Locator;
  readonly submitKycBtn: Locator;
  readonly kycResultBox: Locator;
  readonly kycStatusBadge: Locator;
  readonly kycTierBadge: Locator;
  readonly kycDailyLimit: Locator;
  readonly kycSanctionsBadge: Locator;

  // Fund Transfer
  readonly fundTransferCard: Locator;
  readonly transferForm: Locator;
  readonly selectTransferSource: Locator;
  readonly selectTransferDest: Locator;
  readonly inputTransferAmount: Locator;
  readonly selectTransferDefect: Locator;
  readonly submitTransferBtn: Locator;
  readonly transferResultBox: Locator;
  readonly transferTxnId: Locator;

  // Accounts Overview
  readonly accountsOverviewCard: Locator;
  readonly accountsList: Locator;
  readonly transactionsTable: Locator;
  readonly accountTransactionsWrapper: Locator;

  // Quick Create Account
  readonly quickCreateAccountForm: Locator;
  readonly inputNewHolder: Locator;
  readonly inputNewEmail: Locator;
  readonly selectNewCurrency: Locator;
  readonly selectNewType: Locator;
  readonly inputNewBalance: Locator;
  readonly submitNewAccountBtn: Locator;

  // SWIFT / ISO 20022
  readonly swiftIso20022Card: Locator;
  readonly swiftForm: Locator;
  readonly inputSwiftMsg: Locator;
  readonly inputDebtorIban: Locator;
  readonly inputCreditorIban: Locator;
  readonly inputSwiftAmount: Locator;
  readonly selectSwiftCurrency: Locator;
  readonly submitSwiftBtn: Locator;

  constructor(page: Page) {
    super(page);

    // Root
    this.view = this.byTestId("fintech-view");
    this.banner = this.byTestId("fintech-banner");

    // Feedback
    this.errorBanner = this.byTestId("fintech-error-banner");
    this.successBanner = this.byTestId("fintech-success-banner");

    // KYC
    this.kycOnboardingCard = this.byTestId("kyc-onboarding-card");
    this.kycForm = this.byTestId("kyc-form");
    this.inputKycCustomerId = this.byTestId("input-kyc-customer-id");
    this.inputKycName = this.byTestId("input-kyc-name");
    this.inputKycIncome = this.byTestId("input-kyc-income");
    this.inputKycDob = this.byTestId("input-kyc-dob");
    this.inputKycDoc = this.byTestId("input-kyc-doc");
    this.submitKycBtn = this.byTestId("submit-kyc-btn");
    this.kycResultBox = this.byTestId("kyc-result-box");
    this.kycStatusBadge = this.byTestId("kyc-status-badge");
    this.kycTierBadge = this.byTestId("kyc-tier-badge");
    this.kycDailyLimit = this.byTestId("kyc-daily-limit");
    this.kycSanctionsBadge = this.byTestId("kyc-sanctions-badge");

    // Fund Transfer
    this.fundTransferCard = this.byTestId("fund-transfer-card");
    this.transferForm = this.byTestId("transfer-form");
    this.selectTransferSource = this.byTestId("select-transfer-source");
    this.selectTransferDest = this.byTestId("select-transfer-dest");
    this.inputTransferAmount = this.byTestId("input-transfer-amount");
    this.selectTransferDefect = this.byTestId("select-transfer-defect");
    this.submitTransferBtn = this.byTestId("submit-transfer-btn");
    this.transferResultBox = this.byTestId("transfer-result-box");
    this.transferTxnId = this.byTestId("transfer-txn-id");

    // Accounts Overview
    this.accountsOverviewCard = this.byTestId("accounts-overview-card");
    this.accountsList = this.byTestId("accounts-list");
    this.transactionsTable = this.byTestId("transactions-table");
    this.accountTransactionsWrapper = this.byTestId("account-transactions-wrapper");

    // Quick Create Account
    this.quickCreateAccountForm = this.byTestId("quick-create-account-form");
    this.inputNewHolder = this.byTestId("input-new-holder");
    this.inputNewEmail = this.byTestId("input-new-email");
    this.selectNewCurrency = this.byTestId("select-new-currency");
    this.selectNewType = this.byTestId("select-new-type");
    this.inputNewBalance = this.byTestId("input-new-balance");
    this.submitNewAccountBtn = this.byTestId("submit-new-account-btn");

    // SWIFT / ISO 20022
    this.swiftIso20022Card = this.byTestId("swift-iso20022-card");
    this.swiftForm = this.byTestId("swift-form");
    this.inputSwiftMsg = this.byTestId("input-swift-msg");
    this.inputDebtorIban = this.byTestId("input-debtor-iban");
    this.inputCreditorIban = this.byTestId("input-creditor-iban");
    this.inputSwiftAmount = this.byTestId("input-swift-amount");
    this.selectSwiftCurrency = this.byTestId("select-swift-currency");
    this.submitSwiftBtn = this.byTestId("submit-swift-btn");
  }

  /** Navigate to root, authenticate with demo credentials, then switch to FinTech domain. */
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

    await this.selectFinTechDomain();
  }

  /** Click the FinTech domain tab. */
  async selectFinTechDomain() {
    const domainBtn = this.byTestId("domain-select-fintech");
    await expect(domainBtn).toBeVisible({ timeout: 8000 });
    await domainBtn.click();
    await expect(this.view).toBeVisible({ timeout: 8000 });
  }

  /** Submit KYC verification form. */
  async verifyKYC(opts: {
    customerId?: string;
    name?: string;
    income?: string;
    dob?: string;
    docNumber?: string;
  }) {
    const previousResult = await this.kycResultBox.count();
    if (opts.customerId) await this.inputKycCustomerId.fill(opts.customerId);
    if (opts.name) await this.inputKycName.fill(opts.name);
    if (opts.income) await this.inputKycIncome.fill(opts.income);
    if (opts.dob) await this.inputKycDob.fill(opts.dob);
    if (opts.docNumber) await this.inputKycDoc.fill(opts.docNumber);
    await this.submitKycBtn.click();
    await expect(this.kycResultBox.or(this.errorBanner)).toBeVisible({ timeout: 12000 });
    if (await this.errorBanner.isVisible()) {
      throw new Error(`KYC submission failed: ${await this.errorBanner.innerText()}`);
    }
    await expect(this.kycResultBox).toHaveCount(previousResult + 1, { timeout: 12000 });
    await expect(this.kycResultBox).toBeVisible();
  }

  /** Submit a double-entry fund transfer. */
  async executeTransfer(opts: {
    amount: string;
    defect?: string;
  }) {
    await this.inputTransferAmount.fill(opts.amount);
    if (opts.defect) {
      try {
        await this.selectTransferDefect.selectOption(opts.defect);
      } catch {
        await this.selectTransferDefect.selectOption({ label: new RegExp(opts.defect, "i") });
      }
    }
    await this.submitTransferBtn.click();
    await expect(this.transferResultBox.or(this.errorBanner)).toBeVisible({ timeout: 12000 });
  }

  /** Submit SWIFT / ISO 20022 credit transfer. */
  async submitSwiftTransfer(opts?: {
    amount?: string;
    currency?: string;
  }) {
    if (opts?.amount) await this.inputSwiftAmount.fill(opts.amount);
    if (opts?.currency) await this.selectSwiftCurrency.selectOption(opts.currency);
    await this.submitSwiftBtn.click();
  }

  /** Create a new bank account via the Quick Create form. */
  async createAccount(opts: {
    holder: string;
    email: string;
    currency?: string;
    type?: string;
    initialBalance?: string;
  }) {
    await this.inputNewHolder.fill(opts.holder);
    await this.inputNewEmail.fill(opts.email);
    if (opts.currency) await this.selectNewCurrency.selectOption(opts.currency);
    if (opts.type) await this.selectNewType.selectOption(opts.type);
    if (opts.initialBalance) await this.inputNewBalance.fill(opts.initialBalance);
    await this.submitNewAccountBtn.click();
    await expect(this.successBanner).toBeVisible({ timeout: 12000 });
  }
}
