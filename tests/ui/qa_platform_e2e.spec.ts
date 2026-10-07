import { expect, test } from "@playwright/test";

test.describe("QA Platform Intelligence & Quality Gate E2E Suite", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Switch to QA Platform Tab
    await page.locator('[data-testid="tab-qa-platform"]').click();
  });

  test("Scenario 1: Inspect QA Architecture Overview and Platform Metrics", async ({ page }) => {
    // Top stats validation (475 total capabilities across 11 layers)
    await expect(page.locator(".stat-value").first()).toHaveText("475");
    await expect(page.locator(".stat-card").nth(1)).toContainText("PASSED");

    // Architecture Overview verification
    await expect(page.locator("h2.card-title")).toContainText("Connected Quality Engineering Platform");
    await expect(page.locator(".card")).toContainText("1. System Under Test (SUT)");
    await expect(page.locator(".card")).toContainText("2. QA Engine & Gates");
    await expect(page.locator(".card")).toContainText("3. AI Engine & RAG");
    await expect(page.locator(".card")).toContainText("4. CI/CD & Automation");
  });

  test("Scenario 2: Inspect Intentional Defect Engineering Catalog", async ({ page }) => {
    // Navigate to Defects subtab
    await page.locator('[data-testid="qa-subtab-defects"]').click();

    // Verify defect catalog header
    await expect(page.locator("h2.card-title")).toContainText("Engineered Defect Catalog");

    // Assert key intentional defects exist
    await expect(page.locator('[data-testid="defect-card-OVERBOOKING_RACE"]')).toBeVisible();
    await expect(page.locator('[data-testid="defect-card-CALCULATION_DRIFT"]')).toBeVisible();
    await expect(page.locator('[data-testid="defect-card-STALE_INVENTORY"]')).toBeVisible();
    await expect(page.locator('[data-testid="defect-card-UPSTREAM_GATEWAY_TIMEOUT"]')).toBeVisible();
    await expect(page.locator('[data-testid="defect-card-SCHEMA_CONTRACT_VIOLATION"]')).toBeVisible();
  });

  test("Scenario 3: AI RAG Knowledge Assistant & Defect RCA Diagnosis", async ({ page }) => {
    // Navigate to AI subtab
    await page.locator('[data-testid="qa-subtab-ai"]').click();

    // 1. Test RAG Query
    await page.locator('[data-testid="rag-query-input"]').fill("What is the baggage policy?");
    await page.locator('[data-testid="rag-query-btn"]').click();

    await expect(page.locator('[data-testid="rag-result-box"]')).toBeVisible();
    await expect(page.locator('[data-testid="rag-result-box"]')).toContainText("Synthesized Response");
    await expect(page.locator('[data-testid="rag-result-box"]')).toContainText("Groundedness Score:");

    // 2. Test Defect RCA Agent
    await page.locator('[data-testid="run-rca-btn"]').click();
    await expect(page.locator('[data-testid="rca-result-box"]')).toBeVisible();
    await expect(page.locator('[data-testid="rca-result-box"]')).toContainText("RCA Findings:");
    await expect(page.locator('[data-testid="rca-result-box"]')).toContainText("Recommended Fix:");
  });

  test("Scenario 4: Interactive Quality Gate Evaluation (Approve vs Block)", async ({ page }) => {
    // Navigate to Quality Gate subtab
    await page.locator('[data-testid="qa-subtab-gate"]').click();

    // 1. Evaluate clean run -> APPROVED
    await page.locator('[data-testid="evaluate-gate-btn"]').click();
    await expect(page.locator('[data-testid="gate-evaluation-result"]')).toBeVisible();
    await expect(page.locator('[data-testid="gate-evaluation-result"]')).toContainText("RELEASE APPROVED");

    // 2. Simulate 4 failed tests -> BLOCKED
    await page.locator("#gate-failed").fill("4");
    await page.locator('[data-testid="evaluate-gate-btn"]').click();
    await expect(page.locator('[data-testid="gate-evaluation-result"]')).toContainText("RELEASE BLOCKED");
    await expect(page.locator('[data-testid="gate-evaluation-result"]')).toContainText("Gate Policy Violations:");
  });

  test("Scenario 5: Interactive Regression Impact Simulator, Test Runner & AI Executive Sign-Off", async ({ page }) => {
    // Navigate to Test Runner subtab
    await page.locator('[data-testid="qa-subtab-runner"]').click();

    // 1. Verify Regression Impact Selector
    await expect(page.locator("h2.card-title").first()).toContainText("Intelligent Regression Impact Selector");
    await expect(page.locator("body")).toContainText("Targeted Test Impact Set");

    // 2. Execute Test Suite
    await page.locator('[data-testid="run-test-suite-btn"]').click();

    // Wait for execution completion
    await expect(page.locator(".stat-value", { hasText: "100% Pass Rate" }).or(page.locator(".stat-label", { hasText: "Suite Duration" }))).toBeVisible({ timeout: 5000 });
    await expect(page.locator("body")).toContainText("Quality Gate Status");

    // 3. Generate AI Release Sign-Off Report
    await page.locator('[data-testid="generate-release-report-btn"]').click();
    await expect(page.locator("body")).toContainText("Executive Release Report Generated");
    await expect(page.locator("body")).toContainText("GO — APPROVED FOR RELEASE");
  });

  test("Scenario 6: Interactive Playwright Self-Healing Studio & Stress Benchmarks", async ({ page }) => {
    // Navigate to Self-Heal subtab
    await page.locator('[data-testid="qa-subtab-self-heal"]').click();

    // 1. Verify Self-Healing Studio
    await expect(page.locator("h2.card-title").first()).toContainText("Playwright Self-Healing UI Studio");
    await page.locator('[data-testid="heal-selector-btn"]').click();
    await expect(page.locator('[data-testid="heal-result-box"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="heal-result-box"]')).toContainText("Healed Locator:");
    await expect(page.locator('[data-testid="heal-result-box"]')).toContainText("Confidence");

    // 2. Verify High-Concurrency Stress Benchmark
    await expect(page.locator("body")).toContainText("High-Concurrency Load & Stress Benchmark");
    await page.locator('[data-testid="run-stress-btn"]').click();
    await expect(page.locator('[data-testid="stress-result-box"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="stress-result-box"]')).toContainText("THROUGHPUT");
    await expect(page.locator('[data-testid="stress-result-box"]')).toContainText("p95 LATENCY");
  });
});
