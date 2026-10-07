import { expect, test } from "@playwright/test";

test.describe("UI/UX Modernization: Demo Auth Removal & Light/Dark Theme Governance", () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test to ensure deterministic clean initial state
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.locator('[data-testid="health-status-pill"]')).toBeVisible({ timeout: 15000 });
  });

  test("TEST A — Production booking page has no demo login UI", async ({ page }) => {
    // Verify all obsolete demo login inputs and buttons are completely absent from the DOM
    const demoEmailInput = page.locator('input[aria-label="Demo email"]');
    const demoPasswordInput = page.locator('input[aria-label="Demo password"]');
    const loginButton = page.locator('[data-testid="login-btn"]');
    const loginForm = page.locator('[data-testid="demo-login-form"]');
    const authStatusPill = page.locator('[data-testid="auth-status"]');

    await expect(demoEmailInput).toHaveCount(0);
    await expect(demoPasswordInput).toHaveCount(0);
    await expect(loginButton).toHaveCount(0);
    await expect(loginForm).toHaveCount(0);
    await expect(authStatusPill).toHaveCount(0);

    // Verify absence of any demo authentication warning or gate text
    await expect(page.locator('text="Demo authentication is disabled in production"')).toHaveCount(0);
    await expect(page.locator('text="Sign in with a demo passenger account"')).toHaveCount(0);

    // Verify legitimate search controls are directly rendered and interactive
    await expect(page.locator('[data-testid="origin-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="destination-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-flights-btn"]')).toBeVisible();
  });

  test("TEST B — Booking flow proceeds directly to passenger information without authentication", async ({ page }) => {
    // 1. Search for available flights
    const originSelect = page.locator('[data-testid="origin-select"]');
    const destinationSelect = page.locator('[data-testid="destination-select"]');
    const searchButton = page.locator('[data-testid="search-flights-btn"]');

    await expect(originSelect.locator("option").first()).toBeAttached();
    await originSelect.selectOption("ATH");
    await destinationSelect.selectOption("SKG");
    await searchButton.click();

    // 2. Select first available flight card
    const firstFlightCard = page.locator('[data-testid^="flight-card-"]').first();
    await expect(firstFlightCard).toBeVisible({ timeout: 10000 });
    const selectFlightButton = page.locator('button[data-testid^="select-flight-"]').first();
    await selectFlightButton.click();

    // 3. Verify Passenger Information form is immediately accessible without any login gate
    const passengerNameInput = page.locator('[data-testid="passenger-name-input"]');
    const passengerEmailInput = page.locator('[data-testid="passenger-email-input"]');
    const seatsSelect = page.locator('[data-testid="seats-select"]');
    const createBookingButton = page.locator('[data-testid="create-booking-btn"]');

    await expect(passengerNameInput).toBeVisible();
    await expect(passengerEmailInput).toBeVisible();
    await expect(seatsSelect).toBeVisible();
    await expect(createBookingButton).toBeVisible();

    // 4. Verify no auth blocking card or message is present in the DOM
    await expect(page.locator('text="Sign in with a demo passenger account to continue booking."')).toHaveCount(0);
    await expect(page.locator('[data-testid="demo-login-form"]')).toHaveCount(0);
  });

  test("TEST C — Theme toggle switches between dark and light themes smoothly", async ({ page }) => {
    const htmlElement = page.locator("html");
    const toggleButton = page.locator('[data-testid="theme-toggle-btn"]');

    // 1. Verify toggle button is visible in the header
    await expect(toggleButton).toBeVisible();

    // 2. Initial state is dark theme
    await expect(htmlElement).toHaveAttribute("data-theme", "dark");
    await expect(toggleButton).toHaveAttribute("aria-label", "Switch to light mode");
    await expect(toggleButton).toContainText("Light Mode");

    // 3. Click to switch to light theme
    await toggleButton.click();

    // 4. Verify DOM and accessibility attributes update to light mode
    await expect(htmlElement).toHaveAttribute("data-theme", "light");
    await expect(toggleButton).toHaveAttribute("aria-label", "Switch to dark mode");
    await expect(toggleButton).toContainText("Dark Mode");

    // 5. Click again to switch back to dark theme
    await toggleButton.click();
    await expect(htmlElement).toHaveAttribute("data-theme", "dark");
    await expect(toggleButton).toHaveAttribute("aria-label", "Switch to light mode");
    await expect(toggleButton).toContainText("Light Mode");
  });

  test("TEST D — Theme persistence survives page reload (Light Mode)", async ({ page }) => {
    const htmlElement = page.locator("html");
    const toggleButton = page.locator('[data-testid="theme-toggle-btn"]');

    // Switch to light mode
    await toggleButton.click();
    await expect(htmlElement).toHaveAttribute("data-theme", "light");

    // Verify localStorage has persisted "light"
    const storedThemeBefore = await page.evaluate(() => localStorage.getItem("qa_hub_theme"));
    expect(storedThemeBefore).toBe("light");

    // Reload page
    await page.reload();
    await expect(page.locator('[data-testid="health-status-pill"]')).toBeVisible({ timeout: 15000 });

    // Verify light theme remains active after page reload
    await expect(htmlElement).toHaveAttribute("data-theme", "light");
    await expect(page.locator('[data-testid="theme-toggle-btn"]')).toHaveAttribute("aria-label", "Switch to dark mode");
    const storedThemeAfter = await page.evaluate(() => localStorage.getItem("qa_hub_theme"));
    expect(storedThemeAfter).toBe("light");
  });

  test("TEST E — Theme persistence survives page reload (Dark Mode switch-back)", async ({ page }) => {
    const htmlElement = page.locator("html");
    const toggleButton = page.locator('[data-testid="theme-toggle-btn"]');

    // Switch to light mode first
    await toggleButton.click();
    await expect(htmlElement).toHaveAttribute("data-theme", "light");

    // Switch back to dark mode
    await toggleButton.click();
    await expect(htmlElement).toHaveAttribute("data-theme", "dark");

    // Reload page
    await page.reload();
    await expect(page.locator('[data-testid="health-status-pill"]')).toBeVisible({ timeout: 15000 });

    // Verify dark theme remains active after page reload
    await expect(htmlElement).toHaveAttribute("data-theme", "dark");
    await expect(page.locator('[data-testid="theme-toggle-btn"]')).toHaveAttribute("aria-label", "Switch to light mode");
    const storedTheme = await page.evaluate(() => localStorage.getItem("qa_hub_theme"));
    expect(storedTheme).toBe("dark");
  });

  test("TEST F — Accessibility & keyboard interaction on theme toggle", async ({ page }) => {
    const toggleButton = page.locator('[data-testid="theme-toggle-btn"]');
    const htmlElement = page.locator("html");

    // 1. Semantic button check
    await expect(toggleButton).toHaveAttribute("type", "button");
    await expect(toggleButton).toHaveAttribute("aria-label", /Switch to (light|dark) mode/);

    // 2. Focus via keyboard
    await toggleButton.focus();
    await expect(toggleButton).toBeFocused();

    // 3. Activate via Enter key
    await page.keyboard.press("Enter");
    await expect(htmlElement).toHaveAttribute("data-theme", "light");

    // 4. Activate via Space key
    await page.keyboard.press("Space");
    await expect(htmlElement).toHaveAttribute("data-theme", "dark");
  });
});
