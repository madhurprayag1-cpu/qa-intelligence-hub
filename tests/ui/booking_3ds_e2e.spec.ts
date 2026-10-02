import { expect, test } from "@playwright/test";
import { BookingTrackerPage } from "./pages/BookingTrackerPage";
import { FlightBookingPage } from "./pages/FlightBookingPage";

/**
 * Generates unique synthetic passenger data to guarantee test isolation
 * and prevent data collisions across test runs (AGENTS.md Section 12).
 */
function generateSyntheticPassenger(rolePrefix: string) {
  const timestamp = Date.now();
  const token = Math.random().toString(36).substring(2, 7);
  return {
    name: `${rolePrefix} ${token.toUpperCase()}`,
    email: `e2e.${rolePrefix.toLowerCase().replace(/\s+/g, ".")}.${timestamp}.${token}@synthetic.qahub.io`,
  };
}

const apiBase = process.env.BASE_URL || "http://127.0.0.1:8000";

async function getAdminAuthHeaders(request: any): Promise<{ Authorization: string }> {
  const resp = await request.post(`${apiBase}/auth/login`, {
    data: { email: "admin@qahub.io", password: "admin123" },
  });
  if (resp && resp.ok()) {
    const data = await resp.json();
    return { Authorization: `Bearer ${data.access_token}` };
  }
  return { Authorization: "" };
}

test.describe("Flight Booking & 3DS Payment E2E Suite", () => {
  let activeBookingPage: FlightBookingPage | null = null;

  test.afterEach(async ({ request, page }) => {
    // Automated safe teardown: restore seat inventory and release booking hold
    const authHeaders = await getAdminAuthHeaders(request);
    let bookingId = activeBookingPage?.lastCreatedBooking?.id;

    if (!bookingId) {
      const refLocator = page.locator('[data-testid="receipt-booking-reference"]');
      if (await refLocator.isVisible().catch(() => false)) {
        const ref = (await refLocator.innerText().catch(() => ""))?.trim();
        if (ref && ref.startsWith("QAH-")) {
          const refResp = await request.get(`${apiBase}/bookings/reference/${ref}`, { headers: authHeaders }).catch(() => null);
          if (refResp && refResp.ok()) {
            const data = await refResp.json();
            bookingId = data.id;
          }
        }
      }
    }

    if (bookingId) {
      try {
        const checkResp = await request.get(`${apiBase}/bookings/${bookingId}`, { headers: authHeaders }).catch(() => null);
        if (checkResp && checkResp.ok()) {
          const bookingData = await checkResp.json();
          if (bookingData.status !== "CANCELLED") {
            const cancelResp = await request.post(`${apiBase}/bookings/${bookingId}/cancel`, { headers: authHeaders }).catch(() => null);
            if (cancelResp && cancelResp.ok()) {
              const cancelData = await cancelResp.json();
              console.log(
                `[E2E Teardown] Released ${cancelData.seats_released} seat(s) for booking ${bookingData.reference} (Status: CANCELLED, Refund: ${cancelData.refund_status})`
              );
            } else {
              throw new Error(`[E2E Teardown Failure] POST /bookings/${bookingId}/cancel failed with status ${cancelResp?.status()}`);
            }
          } else {
            console.log(
              `[E2E Teardown] Booking ${bookingData.reference} already in terminal CANCELLED state (seats already restored)`
            );
          }
        } else {
          throw new Error(`[E2E Teardown Failure] GET /bookings/${bookingId} verification failed`);
        }
      } catch (err) {
        console.error(`[E2E Teardown Failure] Cleanup for booking ${bookingId} encountered error:`, err);
        throw err;
      }
    }

    activeBookingPage = null;
  });

  test("Scenario 1: Complete E2E Journey with 3DS SUCCESS authorization", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("Jane QA");

    // Search Flights
    await bookingPage.searchFlights("ATH", "SKG");

    // Select Flight & Enter Details
    await bookingPage.selectFirstAvailableFlight();
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 1);

    // Select 3DS Payment with SUCCESS outcome
    await bookingPage.select3DSChallengeOutcome("SUCCESS");
    await bookingPage.authorizePayment();

    // Verify Receipt
    await expect(bookingPage.receiptStatusBadge).toContainText("TRANSACTION SUCCESSFUL");
    await expect(bookingPage.receiptBookingStatus).toHaveText("PAID");
  });

  test("Scenario 2: 3DS FAILED authentication challenge simulation", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("Alex SDET");

    // Search Flights
    await bookingPage.searchFlights("ATH", "SKG");

    // Select Flight & Enter Details
    await bookingPage.selectFirstAvailableFlight();
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 2);

    // Select 3DS Payment with FAILED outcome
    await bookingPage.select3DSChallengeOutcome("FAILED");
    await bookingPage.authorizePayment();

    // Verify Receipt reflects decline
    await expect(bookingPage.receiptStatusBadge).toContainText("TRANSACTION FAILED");
    await expect(bookingPage.receiptBookingStatus).toHaveText("CONFIRMED");
    await expect(bookingPage.receiptCard).toContainText("3DS_AUTH_FAILED");
  });

  test("Scenario 3: Direct frictionless Credit Card payment", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("Carlos Lead QA");

    // Search Flights
    await bookingPage.searchFlights("ATH", "SKG");

    // Select Flight & Enter Details
    await bookingPage.selectFirstAvailableFlight();
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 1);

    // Select Direct Credit Card
    await bookingPage.selectCreditCardDirect();
    await bookingPage.authorizePayment();

    // Verify Direct Authorization Success
    await expect(bookingPage.receiptStatusBadge).toContainText("TRANSACTION SUCCESSFUL");
    await expect(bookingPage.receiptBookingStatus).toHaveText("PAID");
  });

  test("Scenario 4: Track booking by reference code in Booking Tracker", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    const trackerPage = new BookingTrackerPage(page);

    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("Tracking User");

    // Complete a quick booking to get a live reference
    await bookingPage.searchFlights("ATH", "SKG");
    await bookingPage.selectFirstAvailableFlight();
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 1);
    await bookingPage.selectCreditCardDirect();
    await bookingPage.authorizePayment();

    // Get the reference from the receipt
    const reference = (await page.locator('[data-testid="receipt-booking-reference"]').innerText()).trim();
    expect(reference).toMatch(/^QAH-[A-F0-9]{8}$/);

    // Navigate to tracker tab and lookup
    await trackerPage.navigateToTracker();
    await trackerPage.searchBooking(reference);

    // Assert lookup details
    await expect(trackerPage.lookupResult).toBeVisible();
    await expect(trackerPage.lookupResult).toContainText(reference);
    await expect(trackerPage.lookupResult).toContainText(passenger.name);
    await expect(trackerPage.lookupResult).toContainText("Payment Transaction Audit");
  });

  test("Scenario 5: Cancel booking and verify refund and status transition in tracker", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    const trackerPage = new BookingTrackerPage(page);

    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("Cancel User");

    // Create booking
    await bookingPage.searchFlights("ATH", "SKG");
    await bookingPage.selectFirstAvailableFlight();
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 1);
    await bookingPage.selectCreditCardDirect();
    await bookingPage.authorizePayment();

    const reference = (await page.locator('[data-testid="receipt-booking-reference"]').innerText()).trim();

    // Navigate to tracker
    await trackerPage.navigateToTracker();
    await trackerPage.searchBooking(reference);

    await expect(trackerPage.lookupResult).toBeVisible();
    await expect(trackerPage.lookupResult).toContainText("PAID");

    // Click cancel booking button
    const cancelBtn = page.locator('[data-testid="cancel-booking-btn"]');
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();

    // Verify status transitions to CANCELLED and refund occurs
    await expect(trackerPage.lookupResult).toContainText("CANCELLED");
    await expect(trackerPage.lookupResult).toContainText("REFUNDED");
  });

  test("Scenario 6: End-to-end booking with customized ancillary package and tracker verification", async ({ page }) => {
    const bookingPage = new FlightBookingPage(page);
    activeBookingPage = bookingPage;
    const trackerPage = new BookingTrackerPage(page);

    await bookingPage.goto();

    const passenger = generateSyntheticPassenger("VIP Passenger");

    await bookingPage.searchFlights("ATH", "SKG");
    await bookingPage.selectFirstAvailableFlight();

    // Select custom ancillaries (1 checked bag, extra legroom seat, gourmet meal)
    await bookingPage.selectAncillaries(1, "EXTRA_LEGROOM", "GOURMET");
    await bookingPage.enterPassengerDetails(passenger.name, passenger.email, 1);
    await bookingPage.selectCreditCardDirect();
    await bookingPage.authorizePayment();

    const reference = (await page.locator('[data-testid="receipt-booking-reference"]').innerText()).trim();

    // Navigate to tracker and verify ancillary package is displayed
    await trackerPage.navigateToTracker();
    await trackerPage.searchBooking(reference);

    await expect(trackerPage.lookupResult).toBeVisible();
    await expect(trackerPage.lookupResult).toContainText(passenger.name);
    await expect(trackerPage.lookupResult).toContainText("Itemized Ancillary Services Package");
    await expect(trackerPage.lookupResult).toContainText("Extra Legroom");
    await expect(trackerPage.lookupResult).toContainText("PAID");
  });
});
