import React, { useEffect, useState } from "react";
import {
  fetchEcommerceOrders,
  fetchEcommerceProducts,
  processEcommerceCheckout,
  processEcommerceRefund,
  updateEcommerceOrderStatus,
  validateEcommerceCart,
} from "../api";
import type {
  CartItem,
  CartTotals,
  EcommerceOrder,
  EcommerceProduct,
  RefundDisbursement,
} from "../types";

export function EcommerceView() {
  // State: Catalog
  const [products, setProducts] = useState<EcommerceProduct[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [inStockOnly, setInStockOnly] = useState(false);

  // State: Cart
  const [cart, setCart] = useState<CartItem[]>([]);
  const [shippingTier, setShippingTier] = useState<string>("STANDARD");
  const [promoCode, setPromoCode] = useState<string>("");
  const [cartTotals, setCartTotals] = useState<CartTotals | null>(null);

  // State: Checkout Form
  const [customerId, setCustomerId] = useState("CUST-EC-901");
  const [customerEmail, setCustomerEmail] = useState("buyer@qahub.io");
  const [street, setStreet] = useState("123 Quality Engineering Blvd");
  const [city, setCity] = useState("San Francisco");
  const [postalCode, setPostalCode] = useState("94105");
  const [country, setCountry] = useState("US");
  const [checkoutDefect, setCheckoutDefect] = useState<string>("");
  const [lastOrder, setLastOrder] = useState<{
    order_id: string;
    status: string;
    total_amount: number;
  } | null>(null);

  // State: Order Lifecycle & History
  const [orders, setOrders] = useState<EcommerceOrder[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string>("");
  const [targetOrderStatus, setTargetOrderStatus] = useState<string>("PROCESSING");
  const [orderDefect, setOrderDefect] = useState<string>("");

  // State: Returns & RMA Refunds
  const [rmaId, setRmaId] = useState("RMA-EC-1001");
  const [rmaOrderId, setRmaOrderId] = useState("ORD-EC-1001");
  const [rmaSku, setRmaSku] = useState("SKU-HEADPHONES-01");
  const [rmaAmount, setRmaAmount] = useState("79.99");
  const [rmaReason, setRmaReason] = useState("Defective audio jack");
  const [refundDefect, setRefundDefect] = useState<string>("");
  const [lastRefund, setLastRefund] = useState<RefundDisbursement | null>(null);

  // Feedback & Loading
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadProducts = async () => {
    try {
      const items = await fetchEcommerceProducts(
        selectedCategory || undefined,
        inStockOnly
      );
      setProducts(items);
      // Preload 1 sample item into cart if empty
      if (cart.length === 0 && items.length > 0) {
        const first = items[0];
        setCart([{ sku: first.sku, name: first.name, quantity: 1, unit_price: first.price }]);
      }
    } catch {
      // Hermetic fallback
    }
  };

  const loadOrders = async () => {
    try {
      const list = await fetchEcommerceOrders();
      setOrders(list);
      if (list.length > 0 && !selectedOrderId) {
        setSelectedOrderId(list[0].order_id);
        setRmaOrderId(list[0].order_id);
      }
    } catch {
      // Hermetic fallback
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchEcommerceProducts()
      .then((items) => {
        if (!isMounted) return;
        setProducts(items);
        if (items.length > 0) {
          const first = items[0];
          setCart([{ sku: first.sku, name: first.name, product_name: first.name, quantity: 1, unit_price: first.price }]);
        }
      })
      .catch(() => {});

    fetchEcommerceOrders()
      .then((list) => {
        if (!isMounted) return;
        setOrders(list);
        if (list.length > 0) {
          setSelectedOrderId(list[0].order_id);
          setRmaOrderId(list[0].order_id);
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  // Add product to cart
  const handleAddToCart = (product: EcommerceProduct) => {
    setCart((prev) => {
      const existing = prev.find((item) => item.sku === product.sku);
      if (existing) {
        return prev.map((item) =>
          item.sku === product.sku ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { sku: product.sku, name: product.name, product_name: product.name, quantity: 1, unit_price: product.price }];
    });
    setSuccessMsg(`Added ${product.name} to cart.`);
  };

  // Adjust cart item quantity
  const handleUpdateQuantity = (sku: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) => (item.sku === sku ? { ...item, quantity: item.quantity + delta } : item))
        .filter((item) => item.quantity > 0)
    );
  };

  // 1. Validate Cart & Server-Authoritative Pricing Calculation
  const handleValidateCart = async () => {
    if (cart.length === 0) {
      setError("Shopping cart is empty. Add products to validate.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await validateEcommerceCart({
        items: cart,
        shipping_tier: shippingTier,
        promo_code: promoCode.trim() || undefined,
      });
      setCartTotals(res.totals);
      setSuccessMsg(
        `Cart validated: Subtotal $${res.totals.subtotal.toFixed(2)}, Total: $${res.totals.total_amount.toFixed(2)}.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Cart validation failed");
    } finally {
      setLoading(false);
    }
  };

  // 2. Server-Authoritative Checkout
  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cart.length === 0) {
      setError("Cannot checkout an empty cart.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const payload = {
        cart_id: `CART-${Date.now()}`,
        payment_method: "CREDIT_CARD",
        customer_id: customerId,
        customer_email: customerEmail,
        items: cart,
        shipping_tier: shippingTier,
        shipping_address: { street, city, postal_code: postalCode, country },
        promo_code: promoCode.trim() || undefined,
      };

      const res = await processEcommerceCheckout(
        payload,
        checkoutDefect ? checkoutDefect : undefined
      );

      setLastOrder(res);
      setSuccessMsg(
        `Order ${res.order_id} AUTHORIZED! Authoritative total: $${res.total_amount.toFixed(2)}.`
      );

      // Pre-populate RMA order ID with latest order
      setRmaOrderId(res.order_id);
      if (cart.length > 0) setRmaSku(cart[0].sku);

      // Clear cart & refresh orders
      setCart([]);
      setCartTotals(null);
      await loadOrders();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setLoading(false);
    }
  };

  // 3. Update Order Status
  const handleUpdateOrderStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderId) {
      setError("Select an order to update status.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await updateEcommerceOrderStatus(
        selectedOrderId,
        targetOrderStatus,
        orderDefect ? orderDefect : undefined
      );

      setSuccessMsg(
        `Order ${res.order_id} status updated: transitioned from ${res.previous_status} to ${res.new_status}.`
      );
      await loadOrders();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Order status update failed");
    } finally {
      setLoading(false);
    }
  };

  // 4. Process Refund / Return
  const handleProcessRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const amt = parseFloat(rmaAmount);
      if (isNaN(amt) || amt <= 0) throw new Error("Enter valid refund amount");

      const res = await processEcommerceRefund(
        {
          return_id: rmaId,
          order_id: rmaOrderId,
          sku: rmaSku,
          quantity: 1,
          reason: rmaReason,
          amount: amt,
        },
        refundDefect ? refundDefect : undefined
      );

      setLastRefund(res);
      setSuccessMsg(
        `Refund ${res.refund_id} disbursed: $${res.disbursed_amount.toFixed(2)} for Return ${res.return_id}.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Refund processing failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="domain-view ecommerce-view" data-testid="ecommerce-view">
      {/* Banner */}
      <section className="domain-banner" data-testid="ecommerce-banner">
        <div className="domain-banner-header">
          <div className="domain-badge-group">
            <span className="domain-pill" style={{ background: "rgba(245, 158, 11, 0.2)", color: "#fbbf24", border: "1px solid rgba(245, 158, 11, 0.4)" }}>
              🛒 E-COMMERCE RETAIL SUT
            </span>
            <span className="domain-standard-tag">Server-Authoritative Pricing • Atomic Inventory • Order Lifecycle • Idempotent RMA</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              loadProducts();
              loadOrders();
            }}
            data-testid="ecommerce-refresh-btn"
          >
            🔄 Refresh Catalog & Orders
          </button>
        </div>
        <p className="domain-desc">
          Execute realistic E-Commerce retail journeys: Catalog browsing, dynamic cart price validation,
          server-authoritative checkout with inventory allocation, order state machine lifecycle tracking, and idempotent RMA refund disbursements.
        </p>
      </section>

      {/* Global Alerts */}
      {error && (
        <div className="alert alert-danger fade-in" role="alert" data-testid="ecommerce-error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && !error && (
        <div className="alert alert-success fade-in" role="alert" data-testid="ecommerce-success-banner">
          <span>✅</span>
          <span>{successMsg}</span>
        </div>
      )}

      <div className="domain-grid">
        {/* LEFT COLUMN: Catalog & Cart */}
        <div className="domain-card-column">
          {/* Product Catalog */}
          <section className="form-card" data-testid="catalog-section">
            <div className="card-header-styled">
              <span className="step-num">1</span>
              <div>
                <h3>Product Catalog & Inventory</h3>
                <p className="subtext">Browse synthetic retail products with live inventory quantities</p>
              </div>
            </div>

            <div className="catalog-filters mt-2">
              <select
                aria-label="Filter by category"
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setTimeout(loadProducts, 50);
                }}
                data-testid="select-product-category"
              >
                <option value="">All Categories</option>
                <option value="ELECTRONICS">Electronics</option>
                <option value="APPAREL">Apparel</option>
                <option value="HOME_GOODS">Home Goods</option>
                <option value="ACCESSORIES">Accessories</option>
              </select>
              <label className="checkbox-label text-sm">
                <input
                  type="checkbox"
                  checked={inStockOnly}
                  onChange={(e) => {
                    setInStockOnly(e.target.checked);
                    setTimeout(loadProducts, 50);
                  }}
                  data-testid="checkbox-in-stock-only"
                />
                In Stock Only
              </label>
            </div>

            <div className="product-cards-grid mt-3" data-testid="product-list">
              {products.map((prod) => (
                <div key={prod.sku} className="product-card" data-testid={`product-card-${prod.sku}`}>
                  <div className="product-card-top">
                    <strong className="product-title">{prod.name}</strong>
                    <span className="status-badge badge-active">{prod.category}</span>
                  </div>
                  <div className="product-meta text-sm text-secondary">
                    SKU: <code>{prod.sku}</code>
                  </div>
                  <div className="product-card-bottom mt-2">
                    <div className="product-price">${prod.price.toFixed(2)}</div>
                    <div className="product-stock text-sm">
                      {prod.stock_quantity > 0 ? (
                        <span style={{ color: "#34d399" }}>● {prod.stock_quantity} in stock</span>
                      ) : (
                        <span style={{ color: "#f87171" }}>● Out of stock</span>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm btn-block mt-2"
                    onClick={() => handleAddToCart(prod)}
                    disabled={prod.stock_quantity <= 0}
                    data-testid={`add-to-cart-${prod.sku}`}
                  >
                    🛒 Add to Cart
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* Cart & Authoritative Pricing */}
          <section className="form-card mt-4" data-testid="cart-section">
            <div className="card-header-styled">
              <span className="step-num">2</span>
              <div>
                <h3>Shopping Cart & Authoritative Price Validation</h3>
                <p className="subtext">Calculate server-authoritative taxes, shipping fees, and promotional discounts</p>
              </div>
            </div>

            {cart.length === 0 ? (
              <p className="text-secondary text-sm mt-2">Your cart is empty. Add items from the catalog above.</p>
            ) : (
              <div className="cart-items-table mt-2">
                <table className="data-table" data-testid="cart-items-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Unit Price</th>
                      <th>Qty</th>
                      <th>Subtotal</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cart.map((item) => (
                      <tr key={item.sku} data-testid={`cart-row-${item.sku}`}>
                        <td>
                          <strong>{item.name}</strong>
                          <div className="text-xs text-secondary">{item.sku}</div>
                        </td>
                        <td>${item.unit_price.toFixed(2)}</td>
                        <td>
                          <div className="qty-controls">
                            <button
                              type="button"
                              className="qty-btn"
                              onClick={() => handleUpdateQuantity(item.sku, -1)}
                              data-testid={`qty-minus-${item.sku}`}
                            >
                              -
                            </button>
                            <span className="qty-display" data-testid={`qty-val-${item.sku}`}>
                              {item.quantity}
                            </span>
                            <button
                              type="button"
                              className="qty-btn"
                              onClick={() => handleUpdateQuantity(item.sku, 1)}
                              data-testid={`qty-plus-${item.sku}`}
                            >
                              +
                            </button>
                          </div>
                        </td>
                        <td><strong>${(item.unit_price * item.quantity).toFixed(2)}</strong></td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs"
                            onClick={() => handleUpdateQuantity(item.sku, -item.quantity)}
                            data-testid={`remove-item-${item.sku}`}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="form-row mt-3">
              <div className="form-group flex-1">
                <label htmlFor="ec-shipping-tier">Shipping Method</label>
                <select
                  id="ec-shipping-tier"
                  value={shippingTier}
                  onChange={(e) => setShippingTier(e.target.value)}
                  data-testid="select-shipping-tier"
                >
                  <option value="STANDARD">Standard ($4.99 • 3-5 days)</option>
                  <option value="EXPRESS">Express ($14.99 • 2 days)</option>
                  <option value="OVERNIGHT">Overnight ($29.99 • 1 day)</option>
                </select>
              </div>
              <div className="form-group flex-1">
                <label htmlFor="ec-promo-code">Promo Code (e.g. SUMMER20)</label>
                <input
                  id="ec-promo-code"
                  type="text"
                  placeholder="SUMMER20 or WELCOME10"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value)}
                  data-testid="input-promo-code"
                />
              </div>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-block mt-2"
              onClick={handleValidateCart}
              disabled={loading || cart.length === 0}
              data-testid="validate-cart-btn"
            >
              🧾 Validate & Compute Authoritative Totals
            </button>

            {/* Cart Totals Display */}
            {cartTotals && (
              <div className="status-box mt-3" data-testid="cart-totals-box">
                <div className="price-breakdown-grid">
                  <div className="price-line">
                    <span>Subtotal:</span>
                    <strong>${cartTotals.subtotal.toFixed(2)}</strong>
                  </div>
                  <div className="price-line">
                    <span>Discount:</span>
                    <strong style={{ color: "#34d399" }}>-${cartTotals.discount_amount.toFixed(2)}</strong>
                  </div>
                  <div className="price-line">
                    <span>Shipping:</span>
                    <span>${cartTotals.shipping_cost.toFixed(2)}</span>
                  </div>
                  <div className="price-line">
                    <span>Tax (8%):</span>
                    <span>${cartTotals.tax_amount.toFixed(2)}</span>
                  </div>
                  <hr className="divider mt-1" />
                  <div className="price-line total-line mt-1">
                    <span>Total Authoritative Amount:</span>
                    <strong data-testid="cart-total-amount" style={{ fontSize: "18px", color: "#38bdf8" }}>
                      ${cartTotals.total_amount.toFixed(2)}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN: Server-Authoritative Checkout & Order Lifecycle */}
        <div className="domain-card-column">
          {/* Checkout Card */}
          <section className="form-card" data-testid="checkout-section">
            <div className="card-header-styled">
              <span className="step-num">3</span>
              <div>
                <h3>Server-Authoritative Checkout</h3>
                <p className="subtext">Commit purchase, deduct inventory, and authorize payment</p>
              </div>
            </div>

            <form onSubmit={handleCheckout} data-testid="checkout-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ec-cust-id">Customer ID</label>
                  <input
                    id="ec-cust-id"
                    type="text"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    required
                    data-testid="input-customer-id"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-cust-email">Customer Email</label>
                  <input
                    id="ec-cust-email"
                    type="email"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                    required
                    data-testid="input-customer-email"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="ec-street">Shipping Street Address</label>
                <input
                  id="ec-street"
                  type="text"
                  value={street}
                  onChange={(e) => setStreet(e.target.value)}
                  required
                  data-testid="input-shipping-street"
                />
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ec-city">City</label>
                  <input
                    id="ec-city"
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    required
                    data-testid="input-shipping-city"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-zip">Postal Code</label>
                  <input
                    id="ec-zip"
                    type="text"
                    value={postalCode}
                    onChange={(e) => setPostalCode(e.target.value)}
                    required
                    data-testid="input-shipping-zip"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-country">Country</label>
                  <input
                    id="ec-country"
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    required
                    data-testid="input-shipping-country"
                  />
                </div>
              </div>

              {/* Defect injection hook for checkout */}
              <div className="defect-hook-box">
                <label htmlFor="ec-checkout-defect" className="defect-label">
                  🧪 QA Checkout Defect Hook:
                </label>
                <select
                  id="ec-checkout-defect"
                  value={checkoutDefect}
                  onChange={(e) => setCheckoutDefect(e.target.value)}
                  data-testid="select-checkout-defect"
                >
                  <option value="">None (Standard Authoritative Reconciliation)</option>
                  <option value="DEF-EC-001">
                    DEF-EC-001: Overselling Race Condition (Bypass stock check)
                  </option>
                  <option value="OVERSELLING_RACE">
                    OVERSELLING_RACE (DEF-EC-001)
                  </option>
                  <option value="DEF-EC-002">
                    DEF-EC-002: Promo Stacking Exploit (Excessive discount drift)
                  </option>
                  <option value="PROMO_STACKING_EXPLOIT">
                    PROMO_STACKING_EXPLOIT (DEF-EC-002)
                  </option>
                  <option value="DEF-EC-003">
                    DEF-EC-003: Price Tampering Injection (Accept client asserted total)
                  </option>
                  <option value="PRICE_TAMPERING_INJECTION">
                    PRICE_TAMPERING_INJECTION (DEF-EC-003)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block mt-3"
                disabled={loading || cart.length === 0}
                data-testid="submit-checkout-btn"
              >
                {loading ? "Authorizing..." : "💳 Authorize Payment & Place Order"}
              </button>
            </form>

            {/* Confirmed Order Banner */}
            {lastOrder && (
              <div className="status-box mt-4" data-testid="order-confirmation-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="checkout-order-id">
                    ORDER: {lastOrder.order_id}
                  </span>
                  <span className="status-pill status-pill-online">
                    STATUS: {lastOrder.status}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Authoritative Total:</span>
                    <strong data-testid="checkout-total-amount" style={{ color: "#38bdf8" }}>
                      ${lastOrder.total_amount.toFixed(2)}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Payment Authorization:</span>
                    <span style={{ color: "#10b981" }}>SUCCESS (CAPTURED)</span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Order Lifecycle Pipeline */}
          <section className="form-card mt-4" data-testid="order-lifecycle-section">
            <div className="card-header-styled">
              <span className="step-num">4</span>
              <div>
                <h3>Order Lifecycle State Machine</h3>
                <p className="subtext">Advance order state through strict FSM validation transitions</p>
              </div>
            </div>

            <form onSubmit={handleUpdateOrderStatus} data-testid="order-status-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ec-select-order">Select Order</label>
                  <select
                    id="ec-select-order"
                    value={selectedOrderId}
                    onChange={(e) => setSelectedOrderId(e.target.value)}
                    data-testid="select-order-id"
                  >
                    {orders.map((o) => (
                      <option key={o.order_id} value={o.order_id}>
                        {o.order_id} ({o.status} • ${o.total_amount.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-target-status">Target Status</label>
                  <select
                    id="ec-target-status"
                    value={targetOrderStatus}
                    onChange={(e) => setTargetOrderStatus(e.target.value)}
                    data-testid="select-target-status"
                  >
                    <option value="PAID">PAID</option>
                    <option value="PROCESSING">PROCESSING</option>
                    <option value="SHIPPED">SHIPPED</option>
                    <option value="DELIVERED">DELIVERED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>
              </div>

              {/* Defect injection hook for lifecycle */}
              <div className="defect-hook-box">
                <label htmlFor="ec-lifecycle-defect" className="defect-label">
                  🧪 QA Lifecycle Defect Hook:
                </label>
                <select
                  id="ec-lifecycle-defect"
                  value={orderDefect}
                  onChange={(e) => setOrderDefect(e.target.value)}
                  data-testid="select-lifecycle-defect"
                >
                  <option value="">None (Enforce FSM State Machine)</option>
                  <option value="DEF-EC-004">
                    DEF-EC-004: State Machine Desync (Permits illegal status jump)
                  </option>
                  <option value="ORDER_STATE_DESYNC">
                    ORDER_STATE_DESYNC (DEF-EC-004)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block mt-2"
                disabled={loading || !selectedOrderId}
                data-testid="submit-status-update-btn"
              >
                {loading ? "Updating..." : "🔄 Transition Order Status"}
              </button>
            </form>
          </section>

          {/* Returns & RMA Refunds */}
          <section className="form-card mt-4" data-testid="returns-section">
            <div className="card-header-styled">
              <span className="step-num">5</span>
              <div>
                <h3>Returns & Idempotent RMA Refunds</h3>
                <p className="subtext">Process product returns with idempotency collision protection</p>
              </div>
            </div>

            <form onSubmit={handleProcessRefund} data-testid="refund-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ec-rma-id">Return ID (RMA)</label>
                  <input
                    id="ec-rma-id"
                    type="text"
                    value={rmaId}
                    onChange={(e) => setRmaId(e.target.value)}
                    required
                    data-testid="input-rma-id"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-rma-order">Order ID</label>
                  <input
                    id="ec-rma-order"
                    type="text"
                    value={rmaOrderId}
                    onChange={(e) => setRmaOrderId(e.target.value)}
                    required
                    data-testid="input-rma-order-id"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ec-rma-sku">Returned Product SKU</label>
                  <input
                    id="ec-rma-sku"
                    type="text"
                    value={rmaSku}
                    onChange={(e) => setRmaSku(e.target.value)}
                    required
                    data-testid="input-rma-sku"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ec-rma-amount">Refund Amount ($)</label>
                  <input
                    id="ec-rma-amount"
                    type="number"
                    step="0.01"
                    value={rmaAmount}
                    onChange={(e) => setRmaAmount(e.target.value)}
                    required
                    data-testid="input-rma-amount"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="ec-rma-reason">Return Reason</label>
                <input
                  id="ec-rma-reason"
                  type="text"
                  value={rmaReason}
                  onChange={(e) => setRmaReason(e.target.value)}
                  required
                  data-testid="input-rma-reason"
                />
              </div>

              {/* Defect injection hook for refund */}
              <div className="defect-hook-box">
                <label htmlFor="ec-refund-defect" className="defect-label">
                  🧪 QA Refund Defect Hook:
                </label>
                <select
                  id="ec-refund-defect"
                  value={refundDefect}
                  onChange={(e) => setRefundDefect(e.target.value)}
                  data-testid="select-refund-defect"
                >
                  <option value="">None (Enforce Idempotent Disbursement)</option>
                  <option value="DEF-EC-006">
                    DEF-EC-006: Duplicate Refund Double Credit (Collision Bypass)
                  </option>
                  <option value="REFUND_DOUBLE_CREDIT">
                    REFUND_DOUBLE_CREDIT (DEF-EC-006)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block mt-2"
                disabled={loading}
                data-testid="submit-refund-btn"
              >
                {loading ? "Processing..." : "💸 Disburse RMA Refund"}
              </button>
            </form>

            {lastRefund && (
              <div className="status-box mt-3" data-testid="refund-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="refund-id">
                    REFUND: {lastRefund.refund_id}
                  </span>
                  <span className="status-pill status-pill-online">
                    DISBURSED: ${lastRefund.disbursed_amount.toFixed(2)}
                  </span>
                </div>
                {lastRefund.duplicate_credit && (
                  <div className="alert alert-warning mt-2 text-xs">
                    🚨 DEFECT DETECTED: Duplicate refund payout processed on identical RMA key!
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
