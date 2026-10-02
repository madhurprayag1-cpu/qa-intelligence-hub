import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

/**
 * EcommercePage – Page Object for the E-Commerce (Retail) domain view.
 * Wraps all stable data-testid selectors defined in EcommerceView.tsx.
 */
export class EcommercePage extends BasePage {
  // Root view
  readonly view: Locator;
  readonly banner: Locator;

  // Feedback
  readonly errorBanner: Locator;
  readonly successBanner: Locator;

  // Catalog
  readonly catalogSection: Locator;
  readonly selectProductCategory: Locator;
  readonly checkboxInStockOnly: Locator;
  readonly productList: Locator;

  // Cart
  readonly cartSection: Locator;
  readonly cartItemsTable: Locator;
  readonly cartEmptyMessage: Locator;
  readonly selectShippingTier: Locator;
  readonly inputPromoCode: Locator;
  readonly validateCartBtn: Locator;
  readonly cartTotalsBox: Locator;
  readonly cartTotalAmount: Locator;

  // Checkout
  readonly checkoutSection: Locator;
  readonly checkoutForm: Locator;
  readonly inputCustomerId: Locator;
  readonly inputCustomerEmail: Locator;
  readonly inputShippingStreet: Locator;
  readonly inputShippingCity: Locator;
  readonly inputShippingZip: Locator;
  readonly inputShippingCountry: Locator;
  readonly selectCheckoutDefect: Locator;
  readonly submitCheckoutBtn: Locator;
  readonly orderConfirmationBox: Locator;
  readonly checkoutOrderId: Locator;
  readonly checkoutTotalAmount: Locator;

  // Order Lifecycle
  readonly orderLifecycleSection: Locator;
  readonly orderStatusForm: Locator;
  readonly selectOrderId: Locator;
  readonly selectTargetStatus: Locator;
  readonly selectLifecycleDefect: Locator;
  readonly submitStatusUpdateBtn: Locator;

  // Returns / RMA
  readonly returnsSection: Locator;
  readonly refundForm: Locator;
  readonly inputRmaId: Locator;
  readonly inputRmaOrderId: Locator;
  readonly inputRmaSku: Locator;
  readonly inputRmaAmount: Locator;
  readonly inputRmaReason: Locator;
  readonly selectRefundDefect: Locator;
  readonly submitRefundBtn: Locator;
  readonly refundResultBox: Locator;

  constructor(page: Page) {
    super(page);

    // Root
    this.view = this.byTestId("ecommerce-view");
    this.banner = this.byTestId("ecommerce-banner");

    // Feedback
    this.errorBanner = this.byTestId("ecommerce-error-banner");
    this.successBanner = this.byTestId("ecommerce-success-banner");

    // Catalog
    this.catalogSection = this.byTestId("catalog-section");
    this.selectProductCategory = this.byTestId("select-product-category");
    this.checkboxInStockOnly = this.byTestId("checkbox-in-stock-only");
    this.productList = this.byTestId("product-list");

    // Cart
    this.cartSection = this.byTestId("cart-section");
    this.cartItemsTable = this.byTestId("cart-items-table");
    this.cartEmptyMessage = this.page.getByText("Your cart is empty. Add items from the catalog above.");
    this.selectShippingTier = this.byTestId("select-shipping-tier");
    this.inputPromoCode = this.byTestId("input-promo-code");
    this.validateCartBtn = this.byTestId("validate-cart-btn");
    this.cartTotalsBox = this.byTestId("cart-totals-box");
    this.cartTotalAmount = this.byTestId("cart-total-amount");

    // Checkout
    this.checkoutSection = this.byTestId("checkout-section");
    this.checkoutForm = this.byTestId("checkout-form");
    this.inputCustomerId = this.byTestId("input-customer-id");
    this.inputCustomerEmail = this.byTestId("input-customer-email");
    this.inputShippingStreet = this.byTestId("input-shipping-street");
    this.inputShippingCity = this.byTestId("input-shipping-city");
    this.inputShippingZip = this.byTestId("input-shipping-zip");
    this.inputShippingCountry = this.byTestId("input-shipping-country");
    this.selectCheckoutDefect = this.byTestId("select-checkout-defect");
    this.submitCheckoutBtn = this.byTestId("submit-checkout-btn");
    this.orderConfirmationBox = this.byTestId("order-confirmation-box");
    this.checkoutOrderId = this.byTestId("checkout-order-id");
    this.checkoutTotalAmount = this.byTestId("checkout-total-amount");

    // Order Lifecycle
    this.orderLifecycleSection = this.byTestId("order-lifecycle-section");
    this.orderStatusForm = this.byTestId("order-status-form");
    this.selectOrderId = this.byTestId("select-order-id");
    this.selectTargetStatus = this.byTestId("select-target-status");
    this.selectLifecycleDefect = this.byTestId("select-lifecycle-defect");
    this.submitStatusUpdateBtn = this.byTestId("submit-status-update-btn");

    // Returns / RMA
    this.returnsSection = this.byTestId("returns-section");
    this.refundForm = this.byTestId("refund-form");
    this.inputRmaId = this.byTestId("input-rma-id");
    this.inputRmaOrderId = this.byTestId("input-rma-order-id");
    this.inputRmaSku = this.byTestId("input-rma-sku");
    this.inputRmaAmount = this.byTestId("input-rma-amount");
    this.inputRmaReason = this.byTestId("input-rma-reason");
    this.selectRefundDefect = this.byTestId("select-refund-defect");
    this.submitRefundBtn = this.byTestId("submit-refund-btn");
    this.refundResultBox = this.byTestId("refund-result-box");
  }

  /** Navigate to root, authenticate with demo credentials, then switch to E-Commerce domain. */
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

    await this.selectEcommerceDomain();
  }

  /** Click the E-Commerce domain tab. */
  async selectEcommerceDomain() {
    const domainBtn = this.byTestId("domain-select-ecommerce");
    await expect(domainBtn).toBeVisible({ timeout: 8000 });
    await domainBtn.click();
    await expect(this.view).toBeVisible({ timeout: 8000 });
  }

  /** Add a product to cart by SKU. */
  addToCart(sku: string): Locator {
    return this.byTestId(`add-to-cart-${sku}`);
  }

  /** Get a product card by SKU. */
  productCard(sku: string): Locator {
    return this.byTestId(`product-card-${sku}`);
  }

  /** Get a cart row by SKU. */
  cartRow(sku: string): Locator {
    return this.byTestId(`cart-row-${sku}`);
  }

  /** Get cart quantity display by SKU. */
  cartQtyVal(sku: string): Locator {
    return this.byTestId(`qty-val-${sku}`);
  }

  /**
   * Fill and submit the checkout form.
   * Waits for the order confirmation box to appear.
   */
  async checkout(opts: {
    customerId?: string;
    email?: string;
    street?: string;
    city?: string;
    zip?: string;
    country?: string;
  }) {
    if (opts.customerId) await this.inputCustomerId.fill(opts.customerId);
    if (opts.email) await this.inputCustomerEmail.fill(opts.email);
    if (opts.street) await this.inputShippingStreet.fill(opts.street);
    if (opts.city) await this.inputShippingCity.fill(opts.city);
    if (opts.zip) await this.inputShippingZip.fill(opts.zip);
    if (opts.country) await this.inputShippingCountry.fill(opts.country);
    await this.submitCheckoutBtn.click();
    await expect(this.orderConfirmationBox).toBeVisible({ timeout: 15000 });
  }

  /** Submit an order status transition. */
  async updateOrderStatus(targetStatus: string) {
    await this.selectTargetStatus.selectOption(targetStatus);
    await this.submitStatusUpdateBtn.click();
    await expect(this.successBanner).toBeVisible({ timeout: 12000 });
  }

  /** Submit an RMA refund request. */
  async processRefund(opts: {
    rmaId?: string;
    orderId?: string;
    sku?: string;
    amount?: string;
    reason?: string;
  }) {
    if (opts.rmaId) await this.inputRmaId.fill(opts.rmaId);
    if (opts.orderId) await this.inputRmaOrderId.fill(opts.orderId);
    if (opts.sku) await this.inputRmaSku.fill(opts.sku);
    if (opts.amount) await this.inputRmaAmount.fill(opts.amount);
    if (opts.reason) await this.inputRmaReason.fill(opts.reason);
    await this.submitRefundBtn.click();
  }
}
