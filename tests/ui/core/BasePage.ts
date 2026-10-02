import { expect, Locator, Page } from "@playwright/test";
import { SelfHealingEngine, HealingResult, HealingOptions } from "./SelfHealingEngine";

/**
 * Reusable BasePage for Playwright Page Object Model.
 *
 * Adheres strictly to the Master Architecture Directive:
 * - Domain-independent UI automation foundation.
 * - Standardizes element waits, resilient clicks, fills, screenshots, and ARIA lookups.
 * - Integrates specialist SelfHealingEngine (AGENTS.md Section 6 & 16) for autonomous
 *   locator recovery and strict element verification.
 * - All domain-specific page objects (Airline FlightBookingPage, future Healthcare,
 *   E-commerce, Telecom page objects) inherit from this core base.
 */
export abstract class BasePage {
  readonly page: Page;
  readonly selfHealer: SelfHealingEngine;

  constructor(page: Page, selfHealer?: SelfHealingEngine) {
    this.page = page;
    this.selfHealer = selfHealer || new SelfHealingEngine();
  }

  /**
   * Navigates to a relative or absolute URL and waits for DOM content loaded.
   */
  async navigate(path: string = "/"): Promise<void> {
    await this.page.goto(path);
  }

  /**
   * Helper to retrieve a Locator by stable data-testid attribute.
   */
  byTestId(testId: string): Locator {
    return this.page.locator(`[data-testid="${testId}"]`);
  }

  /**
   * Helper to retrieve a Locator by W3C ARIA accessibility role.
   */
  getByRole(
    role: "button" | "link" | "heading" | "textbox" | "combobox" | "checkbox" | "dialog" | "alert",
    options?: { name?: string | RegExp; exact?: boolean }
  ): Locator {
    return this.page.getByRole(role, options);
  }

  /**
   * Resilient wait for an element to become visible.
   */
  async waitForVisible(locator: Locator, timeoutMs: number = 10000): Promise<void> {
    await expect(locator).toBeVisible({ timeout: timeoutMs });
  }

  /**
   * Resilient click with auto-wait for visibility and enablement.
   */
  async clickElement(locator: Locator, timeoutMs: number = 10000): Promise<void> {
    await this.waitForVisible(locator, timeoutMs);
    await locator.click();
  }

  /**
   * Resilient text input fill.
   */
  async fillField(locator: Locator, value: string, timeoutMs: number = 10000): Promise<void> {
    await this.waitForVisible(locator, timeoutMs);
    await locator.fill(value);
  }

  /**
   * Resilient self-healing click.
   * If the given selector is broken or mutated, autonomously synthesizes
   * and verifies an accessible W3C ARIA locator before clicking.
   * Enforces strict verification: rejects ambiguous matches.
   */
  async clickWithSelfHealing(selector: string, options?: HealingOptions): Promise<HealingResult> {
    return await this.selfHealer.safeClick(this.page, selector, options);
  }

  /**
   * Resilient self-healing text fill.
   */
  async fillWithSelfHealing(selector: string, value: string, options?: HealingOptions): Promise<HealingResult> {
    return await this.selfHealer.safeFill(this.page, selector, value, options);
  }

  /**
   * Safe text content retrieval.
   */
  async getText(locator: Locator): Promise<string> {
    return (await locator.textContent()) || "";
  }

  /**
   * Captures full page screenshot with structured naming.
   */
  async captureScreenshot(name: string): Promise<Buffer> {
    const timestamp = Date.now();
    return await this.page.screenshot({
      path: `test-results/screenshots/${name}_${timestamp}.png`,
      fullPage: false,
    });
  }
}
