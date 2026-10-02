import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

export class BookingTrackerPage extends BasePage {
  readonly tabManage: Locator;
  readonly lookupInput: Locator;
  readonly lookupButton: Locator;
  readonly lookupResult: Locator;

  constructor(page: Page) {
    super(page);
    this.tabManage = this.byTestId("tab-manage");
    this.lookupInput = this.byTestId("lookup-input");
    this.lookupButton = this.byTestId("lookup-btn");
    this.lookupResult = this.byTestId("lookup-result");
  }

  async navigateToTracker() {
    await this.tabManage.click();
    await expect(this.lookupInput).toBeVisible();
  }

  async searchBooking(referenceOrId: string) {
    await this.lookupInput.fill(referenceOrId);
    await this.lookupButton.click();
    await expect(this.lookupResult).toBeVisible();
  }
}
