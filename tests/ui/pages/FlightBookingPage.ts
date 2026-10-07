import { expect, Locator, Page } from "@playwright/test";
import { BasePage } from "../core/BasePage";

export class FlightBookingPage extends BasePage {
  readonly healthStatusPill: Locator;
  readonly originSelect: Locator;
  readonly destinationSelect: Locator;
  readonly searchButton: Locator;
  readonly passengerNameInput: Locator;
  readonly passengerEmailInput: Locator;
  readonly seatsSelect: Locator;
  readonly ancillaryBaggageSelect: Locator;
  readonly ancillarySeatSelect: Locator;
  readonly ancillaryMealSelect: Locator;
  readonly createBookingButton: Locator;
  readonly method3DS: Locator;
  readonly methodCreditCard: Locator;
  readonly challengeBox3DS: Locator;
  readonly payButton: Locator;
  readonly receiptCard: Locator;
  readonly receiptStatusBadge: Locator;
  readonly receiptBookingStatus: Locator;
  lastCreatedBooking?: { id: number; reference: string; seats: number; status?: string };

  constructor(page: Page) {
    super(page);
    this.healthStatusPill = this.byTestId("health-status-pill");
    this.originSelect = this.byTestId("origin-select");
    this.destinationSelect = this.byTestId("destination-select");
    this.searchButton = this.byTestId("search-flights-btn");
    this.passengerNameInput = this.byTestId("passenger-name-input");
    this.passengerEmailInput = this.byTestId("passenger-email-input");
    this.seatsSelect = this.byTestId("seats-select");
    this.ancillaryBaggageSelect = this.byTestId("ancillary-baggage-select");
    this.ancillarySeatSelect = this.byTestId("ancillary-seat-select");
    this.ancillaryMealSelect = this.byTestId("ancillary-meal-select");
    this.createBookingButton = this.byTestId("create-booking-btn");
    this.method3DS = this.byTestId("method-3ds");
    this.methodCreditCard = this.byTestId("method-cc");
    this.challengeBox3DS = this.byTestId("3ds-challenge-box");
    this.payButton = this.byTestId("pay-btn");
    this.receiptCard = this.byTestId("receipt-card");
    this.receiptStatusBadge = this.byTestId("receipt-status-badge");
    this.receiptBookingStatus = this.byTestId("receipt-booking-status");
  }

  async signIn(email: string = "passenger@qahub.io", password: string = "passenger123") {
    // Isolated test-only authentication fixture:
    // Programmatically sets auth token in localStorage for test execution without requiring any UI login form.
    try {
      const apiBase = process.env.BASE_URL || "http://127.0.0.1:8000";
      const resp = await this.page.request.post(`${apiBase}/auth/login`, {
        data: { email, password },
      });
      if (resp && resp.ok()) {
        const data = await resp.json();
        await this.page.evaluate((token) => {
          localStorage.setItem("qa_auth_token", token);
        }, data.access_token);
      }
    } catch {
      // Ignored if /auth/login is unavailable
    }
  }

  async goto() {
    await this.page.goto("/");
    await expect(this.healthStatusPill).toBeVisible();
    await expect(this.healthStatusPill).toContainText(/Backend: HEALTHY/i);
    await this.signIn();
    // Wait for airport dropdowns to be populated from the API
    await expect(this.originSelect.locator("option").first()).toBeAttached();
    await expect(this.destinationSelect.locator("option").first()).toBeAttached();
  }

  async searchFlights(origin: string, destination: string) {
    await expect(this.originSelect.locator(`option[value="${origin}"]`)).toBeAttached();
    await expect(this.destinationSelect.locator(`option[value="${destination}"]`)).toBeAttached();
    await this.originSelect.selectOption(origin);
    await this.destinationSelect.selectOption(destination);
    await this.searchButton.click();
    await expect(this.page.locator('[data-testid^="flight-card-"]').first()).toBeVisible({
      timeout: 10000,
    });
  }

  async selectFirstAvailableFlight() {
    const flightCards = this.page.locator(".flight-card");
    await expect(flightCards.first()).toBeVisible();
    const plentiful = flightCards.filter({ has: this.page.locator(".seats-badge.plenty") });
    if ((await plentiful.count()) > 0) {
      await plentiful.first().locator('button[data-testid^="select-flight-"]').click();
    } else {
      await this.page.locator('[data-testid^="select-flight-"]').first().click();
    }
    await expect(this.passengerNameInput).toBeVisible();
  }

  async selectAncillaries(baggageTier: number, seatPreference: string, mealPreference: string) {
    await this.ancillaryBaggageSelect.selectOption(String(baggageTier));
    await this.ancillarySeatSelect.selectOption(seatPreference);
    await this.ancillaryMealSelect.selectOption(mealPreference);
  }

  async enterPassengerDetails(name: string, email: string, seats: number = 1) {
    await this.passengerNameInput.fill(name);
    await this.passengerEmailInput.fill(email);
    await this.seatsSelect.selectOption(seats.toString());

    const bookingResponsePromise = this.page
      .waitForResponse(
        (resp) =>
          resp.url().includes("/bookings") &&
          resp.request().method() === "POST" &&
          resp.status() === 201,
        { timeout: 10000 }
      )
      .catch(() => null);

    await this.createBookingButton.click();

    const response = await bookingResponsePromise;
    if (response) {
      try {
        const data = await response.json();
        this.lastCreatedBooking = {
          id: data.id,
          reference: data.reference,
          seats: data.seats,
          status: data.status,
        };
      } catch {
        // Fallback silently if response body already consumed
      }
    }

    await expect(this.method3DS).toBeVisible();
  }

  async select3DSChallengeOutcome(outcome: "SUCCESS" | "FAILED" | "TIMEOUT" | "CANCELLED") {
    await this.method3DS.click();
    await expect(this.challengeBox3DS).toBeVisible();
    const outcomeBtn = this.page.locator(`[data-testid="3ds-select-${outcome.toLowerCase()}"]`);
    await outcomeBtn.click();
  }

  async selectCreditCardDirect() {
    await this.methodCreditCard.click();
  }

  async authorizePayment() {
    await this.payButton.click();
    await expect(this.receiptCard).toBeVisible();
  }
}
