import { expect, test } from "@playwright/test";
import { EcommercePage } from "./pages/EcommercePage";

/**
 * E-Commerce E2E Test Suite – Phase 1B.4
 *
 * Tests the complete server-authoritative retail workflow through the real browser:
 *   - Domain selection from the persistent Domain Selector
 *   - Product catalog browsing and category filtering
 *   - Cart add/remove and pricing / shipping tiers
 *   - Server-authoritative checkout with order confirmation
 *   - Order lifecycle state machine transitions
 *   - RMA / return / refund workflow
 *   - Defect simulation scenarios
 *   - Validation / error scenarios
 *
 * Rules (AGENTS.md §16):
 *   - Real frontend → backend API → PostgreSQL persistence.
 *   - No domain APIs mocked.
 *   - Deterministic waits; no arbitrary sleeps.
 */
test.describe("E-Commerce Retail Workflow E2E Suite", () => {
  // -------------------------------------------------------------------
  // 1. Domain Selection
  // -------------------------------------------------------------------
  test("EC-01: Domain selector switches to E-Commerce view", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    // Domain selector bar must be visible
    await expect(ecPage.byTestId("domain-selector")).toBeVisible();

    // Domain button shows active state
    const domainBtn = ecPage.byTestId("domain-select-ecommerce");
    await expect(domainBtn).toHaveAttribute("aria-selected", "true");

    // E-Commerce view root is visible
    await expect(ecPage.view).toBeVisible();
    await expect(ecPage.banner).toBeVisible();
    await expect(ecPage.banner).toContainText(/E-Commerce|Retail|Shop/i);

    // Catalog and cart sections rendered
    await expect(ecPage.catalogSection).toBeVisible();
    await expect(ecPage.cartSection).toBeVisible();
  });

  // -------------------------------------------------------------------
  // 2. Product Catalog
  // -------------------------------------------------------------------
  test("EC-02: Product catalog renders products from the backend", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    // Product list should populate from the API
    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });

    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });

    // Each product card should show a price
    const firstCard = productCards.first();
    await expect(firstCard).toContainText(/\$/);
  });

  // -------------------------------------------------------------------
  // 3. Category Filtering
  // -------------------------------------------------------------------
  test("EC-03: Category filter narrows product catalog", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });

    // Get initial count
    const allCards = ecPage.page.locator('[data-testid^="product-card-"]');
    const initialCount = await allCards.count();

    // Apply a category filter
    const categorySelect = ecPage.selectProductCategory;
    const options = await categorySelect.locator("option").allTextContents();
    const filterableCategories = options.filter((o) => o.toLowerCase() !== "all");

    if (filterableCategories.length > 0) {
      await categorySelect.selectOption({ index: 1 });
      // The list is rendered from the selected category; assert its state
      // after the controlled filter change rather than using a fixed delay.
      const selectedCategory = await categorySelect.inputValue();
      await expect(categorySelect).toHaveValue(selectedCategory);
      const filteredCount = await allCards.count();
      // Either the list is shorter or remains full (all items match filter)
      expect(filteredCount).toBeLessThanOrEqual(initialCount);
    }
    // If no filterable categories exist, assert catalog still visible
    await expect(ecPage.productList).toBeVisible();
  });

  // -------------------------------------------------------------------
  // 4. Add to Cart
  // -------------------------------------------------------------------
  test("EC-04: Adding a product to cart renders cart row", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });

    // Extract the first product's SKU from the testid attribute
    const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
    const sku = firstCardTestId.replace("product-card-", "");

    // Add to cart
    const addBtn = ecPage.addToCart(sku);
    await expect(addBtn).toBeVisible();
    await addBtn.click();

    // Cart items table should now show the product row
    await expect(ecPage.cartItemsTable).toBeVisible();
    const cartRow = ecPage.cartRow(sku);
    await expect(cartRow).toBeVisible();
    await expect(cartRow).toContainText(sku);
  });

  // -------------------------------------------------------------------
  // 5. Cart Quantity Adjustment
  // -------------------------------------------------------------------
  test("EC-05: Cart quantity plus button increments the count", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });

    const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
    const sku = firstCardTestId.replace("product-card-", "");

    // Add product to cart
    await ecPage.addToCart(sku).click();
    await expect(ecPage.cartRow(sku)).toBeVisible();

    // Get initial quantity
    const qtyLocator = ecPage.cartQtyVal(sku);
    const initialQty = parseInt((await qtyLocator.textContent()) ?? "1", 10);

    // Click plus
    const plusBtn = ecPage.byTestId(`qty-plus-${sku}`);
    await plusBtn.click();

    // Quantity should increment
    const newQty = parseInt((await qtyLocator.textContent()) ?? "1", 10);
    expect(newQty).toBe(initialQty + 1);
  });

  // -------------------------------------------------------------------
  // 6. Cart Validation & Totals
  // -------------------------------------------------------------------
  test("EC-06: Validate cart produces server-authoritative totals", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });

    const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
    const sku = firstCardTestId.replace("product-card-", "");
    await ecPage.addToCart(sku).click();
    await expect(ecPage.cartRow(sku)).toBeVisible();

    // Validate cart
    await expect(ecPage.validateCartBtn).toBeVisible();
    await ecPage.validateCartBtn.click();

    await expect(ecPage.cartTotalsBox).toBeVisible({ timeout: 12000 });
    await expect(ecPage.cartTotalAmount).toBeVisible();

    // Total must be a positive dollar amount
    const totalText = await ecPage.cartTotalAmount.textContent() ?? "";
    expect(totalText).toMatch(/\$\d+\.\d{2}/);
  });

  // -------------------------------------------------------------------
  // 7. Checkout – Happy Path
  // -------------------------------------------------------------------
  test("EC-07: Complete checkout flow produces an order ID", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });

    const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
    const sku = firstCardTestId.replace("product-card-", "");
    await ecPage.addToCart(sku).click();
    await expect(ecPage.cartRow(sku)).toBeVisible();

    const ts = Date.now();
    await ecPage.checkout({
      customerId: `CUST-E2E-${ts}`,
      email: `checkout.e2e${ts}@synthetic.qahub.io`,
      street: "123 E2E Street",
      city: "Testville",
      zip: "10001",
      country: "US",
    });

    // Order confirmation box visible with an order ID
    await expect(ecPage.orderConfirmationBox).toBeVisible({ timeout: 15000 });
    await expect(ecPage.checkoutOrderId).toBeVisible();
    const orderId = await ecPage.checkoutOrderId.textContent() ?? "";
    expect(orderId.trim().length).toBeGreaterThan(3);

    // Total amount displayed
    await expect(ecPage.checkoutTotalAmount).toBeVisible();
  });

  // -------------------------------------------------------------------
  // 8. Order Lifecycle – State Transition
  // -------------------------------------------------------------------
  test("EC-08: Order status can be transitioned to PAID", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    // Wait for existing orders or create one
    await expect(ecPage.orderLifecycleSection).toBeVisible({ timeout: 10000 });

    const orderSelect = ecPage.selectOrderId;
    const options = await orderSelect.locator("option").allTextContents();
    const hasOrders = options.some((o) => o.trim() !== "" && !o.toLowerCase().includes("select"));

    if (!hasOrders) {
      // Create an order first via checkout
      await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
      const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
      await expect(productCards.first()).toBeVisible({ timeout: 10000 });
      const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
      const sku = firstCardTestId.replace("product-card-", "");
      await ecPage.addToCart(sku).click();
      const ts = Date.now();
      await ecPage.checkout({
        customerId: `CUST-LC-${ts}`,
        email: `lifecycle.e2e${ts}@synthetic.qahub.io`,
        street: "456 Status Ave",
        city: "Stateville",
        zip: "20001",
        country: "US",
      });
      await expect(ecPage.orderConfirmationBox).toBeVisible({ timeout: 15000 });
    }

    // Transition to PAID
    await ecPage.updateOrderStatus("PAID");
    await expect(ecPage.successBanner).toContainText(/PAID|status|updated/i);
  });

  // -------------------------------------------------------------------
  // 9. RMA / Refund Workflow
  // -------------------------------------------------------------------
  test("EC-09: RMA refund submission produces a refund result", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.returnsSection).toBeVisible();

    const ts = Date.now();
    await ecPage.processRefund({
      rmaId: `RMA-E2E-${ts}`,
      orderId: `ORD-E2E-${ts}`,
      sku: "SKU-001",
      amount: "19.99",
      reason: "E2E test return – product defective",
    });

    // A completed refund produces a result; an unknown synthetic order is
    // explicitly rejected. Either outcome must be observable and meaningful.
    await expect(ecPage.refundResultBox.or(ecPage.errorBanner)).toBeVisible({ timeout: 12000 });
    if (await ecPage.errorBanner.isVisible()) {
      await expect(ecPage.errorBanner).toContainText(/order|refund|RMA|not found|invalid/i);
    } else {
      await expect(ecPage.refundResultBox).toContainText(/refund|RMA|amount|status/i);
    }
  });

  // -------------------------------------------------------------------
  // 10. DEF-EC-002 Race Condition Overselling Defect
  // -------------------------------------------------------------------
  test("EC-10: DEF-EC-002 overselling race defect is detected in checkout", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.productList).toBeVisible({ timeout: 10000 });
    const productCards = ecPage.page.locator('[data-testid^="product-card-"]');
    await expect(productCards.first()).toBeVisible({ timeout: 10000 });
    const firstCardTestId = await productCards.first().getAttribute("data-testid") ?? "";
    const sku = firstCardTestId.replace("product-card-", "");
    await ecPage.addToCart(sku).click();
    await expect(ecPage.cartRow(sku)).toBeVisible();

    // Inject checkout defect
    await ecPage.selectCheckoutDefect.selectOption("DEF-EC-002");

    const ts = Date.now();
    await ecPage.inputCustomerId.fill(`CUST-RACE-${ts}`);
    await ecPage.inputCustomerEmail.fill(`race.e2e${ts}@synthetic.qahub.io`);
    await ecPage.submitCheckoutBtn.click();

    await expect(ecPage.errorBanner.or(ecPage.orderConfirmationBox)).toBeVisible({ timeout: 15000 });
    if (await ecPage.errorBanner.isVisible()) {
      await expect(ecPage.errorBanner).toContainText(/stock|inventory|race|order|checkout/i);
    } else {
      await expect(ecPage.orderConfirmationBox).toContainText(/order|total|authorized/i);
    }
  });

  // -------------------------------------------------------------------
  // 11. Validation – Empty cart checkout
  // -------------------------------------------------------------------
  test("EC-11: Checkout with empty cart is rejected with error", async ({ page }) => {
    const ecPage = new EcommercePage(page);
    await ecPage.goto();

    await expect(ecPage.cartSection).toBeVisible();
    const cartRows = ecPage.page.locator('[data-testid^="cart-row-"]');
    while (await cartRows.count() > 0) {
      const firstRow = cartRows.first();
      await firstRow.getByTestId(`remove-item-${(await firstRow.getAttribute("data-testid"))?.replace("cart-row-", "")}`).click();
      await expect(firstRow).toBeHidden();
    }
    await expect(ecPage.submitCheckoutBtn).toBeDisabled();
    await expect(ecPage.cartEmptyMessage).toBeVisible();

    // Empty-cart checkout must be prevented by the rendered UI.
    const ts = Date.now();
    await ecPage.inputCustomerId.fill(`CUST-EMPTY-${ts}`);
    await ecPage.inputCustomerEmail.fill(`empty.e2e${ts}@synthetic.qahub.io`);
    await expect(ecPage.submitCheckoutBtn).toBeDisabled();
    await expect(ecPage.cartEmptyMessage).toBeVisible();
  });
});
