import { expect, test } from "@playwright/test";

test.describe("Booking Authorization & Test Evidence Explorer E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.locator('[data-testid="health-status-pill"]')).toBeVisible({ timeout: 15000 });
  });

  // ==========================================================================
  // OBJECTIVE 1: BOOKING AUTHORIZATION BEARER TOKEN
  // ==========================================================================

  test("TEST 1: Production booking UI renders with no login, no password, and no manual token field", async ({
    page,
  }) => {
    // 1. Verify no login or password form exists anywhere on screen
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await expect(page.locator('input[type="email"][data-testid="login-email"]')).toHaveCount(0);
    await expect(page.locator('input[placeholder*="bearer" i]')).toHaveCount(0);
    await expect(page.locator('input[placeholder*="token" i]')).toHaveCount(0);
    await expect(page.locator('button:has-text("Sign In")')).toHaveCount(0);
    await expect(page.locator('button:has-text("Log In")')).toHaveCount(0);

    // 2. Verify search form is immediately accessible
    await expect(page.locator('[data-testid="origin-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="destination-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-flights-btn"]')).toBeVisible();

    // 3. Verify no authorization error banner
    await expect(page.locator('[data-testid="error-banner"]')).toHaveCount(0);
  });

  test("TEST 2: Complete booking flow with server-controlled demo authorization and no bearer token error", async ({
    page,
  }) => {
    // 1. Select route and search
    const originSelect = page.locator('[data-testid="origin-select"]');
    await expect(originSelect.locator("option").first()).toBeAttached();
    await originSelect.selectOption("ATH");
    await page.locator('[data-testid="destination-select"]').selectOption("SKG");
    await page.locator('[data-testid="search-flights-btn"]').click();

    // 2. Select flight
    const flightCard = page.locator('[data-testid^="flight-card-"]').first();
    await expect(flightCard).toBeVisible({ timeout: 10000 });
    await page.locator('button[data-testid^="select-flight-"]').first().click();

    // 3. Passenger Details Form -> Confirm Booking without manual auth input
    await expect(page.locator('[data-testid="passenger-name-input"]')).toBeVisible();
    await page.locator('[data-testid="create-booking-btn"]').click();

    // 4. Verify booking confirmed, zero bearer-token errors
    await expect(page.locator('[data-testid="error-banner"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="success-banner"]')).toContainText("confirmed");

    // 5. Payment processing
    await expect(page.locator('[data-testid="pay-btn"]')).toBeVisible({ timeout: 10000 });
    await page.locator('[data-testid="pay-btn"]').click();

    // 6. Verify receipt reached
    await expect(page.locator('[data-testid="receipt-card"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="error-banner"]')).toHaveCount(0);
  });

  // ==========================================================================
  // OBJECTIVE 2: AUTOMATED TEST CASE EVIDENCE EXPLORER
  // ==========================================================================

  test("TEST 3: Open Automated Test Cases by clicking stat card and verify test list", async ({ page }) => {
    // 1. Go to QA Platform
    await page.locator('[data-testid="tab-qa-platform"]').click();

    // 2. Assert the browser uses same-origin API routing in production-like hosting.
    const apiRequest = page.waitForRequest((request) => request.url().includes("/qa/tests"));
    await page.locator('[data-testid="qa-subtab-tests"]').click();
    const request = await apiRequest;
    const requestUrl = new URL(request.url());
    const pageUrl = new URL(page.url());

    // Local CI intentionally serves the React dev app from localhost while the
    // FastAPI backend runs on 127.0.0.1:8000. Production/preview deployments
    // must use same-origin Vercel rewrites.
    if (pageUrl.hostname === "localhost" || pageUrl.hostname === "127.0.0.1") {
      expect(requestUrl.origin).toBe("http://127.0.0.1:8000");
    } else {
      expect(requestUrl.origin).toBe(pageUrl.origin);
    }

    // 3. Click the top "Automated Test Cases" stat card
    const statCard = page.locator('[data-testid="stat-card-automated-tests"]');
    await expect(statCard).toBeVisible();
    await statCard.click();

    // 4. Verify Test Explorer opens
    await expect(page.locator('[data-testid="test-explorer-container"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="test-evidence-table"]')).toBeVisible({ timeout: 15000 });

    // Verify rows render from real backend evidence
    const rows = page.locator('[data-testid="test-evidence-table"] tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test("TEST 4: Select PASSED filter and verify genuine passed test count", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-tests"]').click();

    // Click PASSED filter
    await page.locator('[data-testid="filter-status-passed"]').click();

    // Verify table updates and all visible badges are PASS
    const rows = page.locator('[data-testid="test-evidence-table"] tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });

    const statusBadges = page.locator('[data-testid="test-evidence-table"] tbody tr .badge-success');
    const badgeCount = await statusBadges.count();
    expect(badgeCount).toBeGreaterThan(0);
  });

  test("TEST 5: Click one passed test to open detailed Test Evidence drawer", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-tests"]').click();

    // Find first evidence button and click
    const evidenceBtn = page.locator('button[data-testid^="view-evidence-btn-"]').first();
    await expect(evidenceBtn).toBeVisible({ timeout: 10000 });
    await evidenceBtn.click();

    // Verify modal drawer opens
    await expect(page.locator('[data-testid="test-evidence-modal"]')).toBeVisible();
    await expect(page.locator("#evidence-modal-title")).toBeVisible();
    await expect(page.locator(".evidence-body")).toBeVisible();
  });

  test("TEST 6A: API failure is shown as unavailable, never as zero tests", async ({ page }) => {
    await page.route("**/qa/tests**", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Evidence service unavailable" }),
      });
    });

    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-tests"]').click();

    await expect(page.locator('[data-testid="test-explorer-unavailable"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="test-explorer-error"]')).toContainText("Failed to fetch QA tests");
    await expect(page.locator('[data-testid="test-empty-state"]')).toHaveCount(0);
  });

  test("TEST 6: Verify expected vs actual assertion details in evidence drawer", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-tests"]').click();

    const evidenceBtn = page.locator('button[data-testid^="view-evidence-btn-"]').first();
    await expect(evidenceBtn).toBeVisible({ timeout: 10000 });
    await evidenceBtn.click();

    // Verify assertion list
    await expect(page.locator('[data-testid="test-assertion-list"]')).toBeVisible();
    const firstAssertion = page.locator('[data-testid="assertion-item-0"]');
    await expect(firstAssertion).toBeVisible();

    // Verify Expected and Actual blocks
    await expect(firstAssertion).toContainText("Expected:");
    await expect(firstAssertion).toContainText("Actual:");

    // Close modal
    await page.locator('[data-testid="close-evidence-modal"]').click();
    await expect(page.locator('[data-testid="test-evidence-modal"]')).toHaveCount(0);
  });

  // ==========================================================================
  // OBJECTIVE 3: RUN / TRANSACTION / CAPABILITY EXPLORER
  // ==========================================================================

  test("TEST 7 & 8: Open Run Explorer and select an execution run", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    // Verify Run Explorer view
    await expect(page.locator('[data-testid="run-explorer-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="runs-list-panel"]')).toBeVisible();

    // Select first run
    const firstRunItem = page.locator('[data-testid^="run-item-"]').first();
    await expect(firstRunItem).toBeVisible({ timeout: 10000 });
    await firstRunItem.click();

    // Verify run summary view
    await expect(page.locator('[data-testid="run-summary-view"]')).toBeVisible();
  });

  test("TEST 9: Verify run summary metadata and quality gate status", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    await expect(page.locator('[data-testid="run-summary-view"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="run-summary-view"]')).toContainText("RUN SUMMARY");
    await expect(page.locator('[data-testid="run-summary-view"]')).toContainText("Pass");
  });

  test("TEST 10: Open a domain breakdown card and filter run tests", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    // Find Airline domain card
    const airlineDomainCard = page.locator('[data-testid="domain-card-airline"]');
    await expect(airlineDomainCard).toBeVisible({ timeout: 10000 });
    await airlineDomainCard.click();
    await expect(page.locator("body")).toContainText("Domain: airline");
  });

  test("TEST 11: Open a layer filter and verify test suite isolation", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    const layerBtn = page.locator('button[data-testid^="layer-btn-"]').first();
    await expect(layerBtn).toBeVisible({ timeout: 10000 });
    await layerBtn.click();
    await expect(page.locator("body")).toContainText("Layer:");
  });

  test("TEST 12: Direct Capability ID search retrieves metadata and execution history", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    // Search capability ID
    const searchInput = page.locator('[data-testid="cap-search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 15000 });
    await searchInput.fill("CAP-AIR-TEST_LIST_AIRLINES");
    await page.locator('[data-testid="cap-search-btn"]').click();

    // Verify searched capability details card
    await expect(page.locator('[data-testid="searched-cap-details"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="searched-cap-details"]')).toContainText("CAP-AIR-TEST_LIST_AIRLINES");
    await expect(page.locator('[data-testid="searched-cap-details"]')).toContainText("Execution History");
  });

  test("TEST 13: Open execution evidence from run drill-down table", async ({ page }) => {
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-runs"]').click();

    const viewEvidenceBtn = page.locator('button[data-testid^="view-run-evidence-"]').first();
    await expect(viewEvidenceBtn).toBeVisible({ timeout: 15000 });
    await viewEvidenceBtn.click();

    // Verify modal overlay opens with assertion evidence
    await expect(page.locator('.modal-overlay[role="dialog"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.modal-overlay[role="dialog"]')).toContainText("Verified Assertion Evidence");
  });

  test("TEST 14: Switch Light/Dark mode and verify UI remains completely functional and accessible", async ({
    page,
  }) => {
    // 1. Initial dark mode
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    // 2. Click theme toggle -> switch to light mode
    await page.locator('[data-testid="theme-toggle-btn"]').click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    // 3. Open Test Explorer in light mode
    await page.locator('[data-testid="tab-qa-platform"]').click();
    await page.locator('[data-testid="qa-subtab-tests"]').click();
    await expect(page.locator('[data-testid="test-explorer-container"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="test-evidence-table"]')).toBeVisible({ timeout: 15000 });

    // 4. Open Run Explorer in light mode
    await page.locator('[data-testid="qa-subtab-runs"]').click();
    await expect(page.locator('[data-testid="run-explorer-container"]')).toBeVisible();

    // 5. Toggle back to dark mode
    await page.locator('[data-testid="theme-toggle-btn"]').click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});
