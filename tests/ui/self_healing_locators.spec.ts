import { expect, test } from "@playwright/test";
import { AmbiguousMatchError, HealingFailedError, SelfHealingEngine } from "./core/SelfHealingEngine";
import { FlightBookingPage } from "./pages/FlightBookingPage";

test.describe("Playwright Self-Healing Locator Engine (Task 6.4)", () => {
  let healer: SelfHealingEngine;

  test.beforeEach(() => {
    healer = new SelfHealingEngine(1000);
  });

  test("Scenario 1: Successfully recovers broken XPath to verified accessible ARIA locator", async ({ page }) => {
    // Render realistic component with broken legacy selector target
    await page.setContent(`
      <div class="search-form-container" style="padding: 20px;">
        <h2>Flight Search Engine</h2>
        <form id="search-form">
          <input type="text" placeholder="Origin Airport (e.g. ATH)" id="origin-field" />
          <div class="actions" style="margin-top: 10px;">
            <button
              type="button"
              data-testid="search-flights-btn"
              class="btn btn-primary"
              onclick="document.getElementById('search-result').innerText = 'FLIGHTS_DISCOVERED'"
            >
              Search Flights
            </button>
          </div>
        </form>
        <div id="search-result" style="margin-top: 10px;">AWAITING_SEARCH</div>
      </div>
    `);

    // Intentionally pass a broken hierarchical XPath that does not exist
    const brokenXPath = "//div[99]/form/div[88]/button[77]";

    // Self-healing executes click with autonomous recovery
    const result = await healer.safeClick(page, brokenXPath);

    // Verify healing telemetry and invariants
    expect(result.healed).toBe(true);
    expect(result.status).toBe("VERIFIED");
    expect(result.matchCount).toBe(1);
    expect(result.verified).toBe(true);
    expect(result.healedSelector).toMatch(/getByTestId\('search-flights-btn'\)|getByRole\('button'/);
    expect(result.confidence).toBeGreaterThanOrEqual(0.95);

    // Verify action was actually performed on the verified element
    await expect(page.locator("#search-result")).toHaveText("FLIGHTS_DISCOVERED");
  });

  test("Scenario 2: Strictly rejects ambiguous locator matches and never silently accepts incorrect element", async ({ page }) => {
    // Render multiple identical buttons without distinguishing names or testids
    await page.setContent(`
      <div class="booking-management" style="padding: 20px;">
        <h3>Reservation Actions</h3>
        <div class="row">
          <button class="action-btn" onclick="window.clicked = 'FIRST'">Cancel Reservation</button>
        </div>
        <div class="row">
          <button class="action-btn" onclick="window.clicked = 'SECOND'">Cancel Reservation</button>
        </div>
      </div>
    `);

    const brokenSelector = ".legacy-cancel-v2023";

    // 1. Invariant: throwOnAmbiguous defaults to true and throws AmbiguousMatchError
    await expect(async () => {
      await healer.safeClick(page, brokenSelector, { timeoutMs: 500, throwOnAmbiguous: true });
    }).rejects.toThrow(AmbiguousMatchError);

    // 2. When non-throwing, returns AMBIGUOUS_MATCH with verified=false and count=2
    const nonThrowingResult = await healer.safeClick(page, brokenSelector, {
      timeoutMs: 500,
      throwOnAmbiguous: false,
    });

    expect(nonThrowingResult.healed).toBe(false);
    expect(nonThrowingResult.status).toBe("AMBIGUOUS_MATCH");
    expect(nonThrowingResult.matchCount).toBe(2);
    expect(nonThrowingResult.verified).toBe(false);
    expect(nonThrowingResult.justification).toContain("Ambiguous match rejected");

    // Assert neither button was clicked (no state mutation occurred)
    const clickedVal = await page.evaluate(() => (window as any).clicked);
    expect(clickedVal).toBeUndefined();
  });

  test("Scenario 3: Unrecoverable selector fails explicitly with HealingFailedError", async ({ page }) => {
    // Render static informational container with no actionable elements
    await page.setContent(`
      <div class="read-only-banner" style="padding: 20px;">
        <p>Your session has expired. Please refresh your browser.</p>
      </div>
    `);

    const ghostSelector = "#non-existent-checkout-btn-999";

    // 1. Throws HealingFailedError
    await expect(async () => {
      await healer.safeClick(page, ghostSelector, { timeoutMs: 500, throwOnFailure: true });
    }).rejects.toThrow(HealingFailedError);

    // 2. When non-throwing, returns HEALING_FAILED with matchCount 0
    const failedResult = await healer.safeClick(page, ghostSelector, {
      timeoutMs: 500,
      throwOnFailure: false,
    });

    expect(failedResult.healed).toBe(false);
    expect(failedResult.status).toBe("HEALING_FAILED");
    expect(failedResult.matchCount).toBe(0);
    expect(failedResult.verified).toBe(false);
  });

  test("Scenario 4: Valid original selector resolves immediately without healing overhead", async ({ page }) => {
    await page.setContent(`
      <div style="padding: 20px;">
        <button id="direct-action-btn" onclick="document.getElementById('status').innerText = 'CLICKED'">
          Direct Action
        </button>
        <span id="status">INITIAL</span>
      </div>
    `);

    const result = await healer.safeClick(page, "#direct-action-btn");

    expect(result.healed).toBe(false);
    expect(result.status).toBe("ORIGINAL_RESOLVED");
    expect(result.matchCount).toBe(1);
    expect(result.verified).toBe(true);
    await expect(page.locator("#status")).toHaveText("CLICKED");
  });

  test("Scenario 5: BasePage Page Object integrates self-healing seamlessly", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);

    await page.setContent(`
      <div style="padding: 20px;">
        <button data-testid="search-flights-btn" onclick="window.searched = true">
          Search Flights
        </button>
      </div>
    `);

    // Invoke self-healing through BasePage method
    const result = await bookingPage.clickWithSelfHealing(".old-broken-search-btn-class");

    expect(result.healed).toBe(true);
    expect(result.status).toBe("VERIFIED");
    expect(result.matchCount).toBe(1);

    const searched = await page.evaluate(() => (window as any).searched);
    expect(searched).toBe(true);
  });
});
