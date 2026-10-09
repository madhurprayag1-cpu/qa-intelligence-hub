import { expect, test } from "@playwright/test";
import { FlightBookingPage } from "./pages/FlightBookingPage";

function passenger() {
  const stamp = Date.now();
  return { name: "Payment Form QA", email: `payment.form.${stamp}@synthetic.qahub.io` };
}

test.describe("Airline payment method forms", () => {
  test("card payment requires card fields before authorization", async ({ page }) => {
    const booking = new FlightBookingPage(page);
    await booking.goto();
    const p = passenger();
    await booking.searchFlights("ATH", "SKG");
    await booking.selectFirstAvailableFlight();
    await booking.enterPassengerDetails(p.name, p.email, 1);

    await expect(page.getByTestId("payment-details-form")).toBeVisible();
    await expect(page.getByTestId("payment-cardholder")).toBeVisible();
    await expect(page.getByTestId("payment-card-number")).toBeVisible();
    await expect(page.getByTestId("payment-card-expiry")).toBeVisible();
    await expect(page.getByTestId("payment-card-cvc")).toBeVisible();

    await booking.payButton.click();
    await expect(page.getByTestId("error-banner")).toContainText("cardholder name");
    await expect(booking.receiptCard).toHaveCount(0);
  });

  test("switching methods renders the correct details and cash confirmation", async ({ page }) => {
    const booking = new FlightBookingPage(page);
    await booking.goto();
    const p = passenger();
    await booking.searchFlights("ATH", "SKG");
    await booking.selectFirstAvailableFlight();
    await booking.enterPassengerDetails(p.name, p.email, 1);

    await page.getByTestId("method-cc").click();
    await expect(page.getByTestId("card-payment-fields")).toBeVisible();

    await page.getByTestId("method-3ds").click();
    await expect(page.getByTestId("3ds-challenge-box")).toBeVisible();
    await expect(page.getByTestId("card-payment-fields")).toBeVisible();

    await page.getByText("Debit Card", { exact: true }).click();
    await expect(page.getByTestId("card-payment-fields")).toBeVisible();

    await page.getByText("UPI", { exact: true }).click();
    await expect(page.getByTestId("payment-upi-id")).toBeVisible();

    await page.getByText("Digital Wallet", { exact: true }).click();
    await expect(page.getByTestId("payment-wallet-provider")).toBeVisible();
    await expect(page.getByTestId("payment-wallet-account")).toBeVisible();

    await page.getByText("Easy Pay", { exact: true }).click();
    await expect(page.getByTestId("payment-easy-phone")).toBeVisible();

    await page.getByText("Cash", { exact: true }).click();
    await expect(page.getByTestId("payment-cash-confirm")).toBeVisible();
    await booking.payButton.click();
    await expect(page.getByTestId("error-banner")).toContainText("Confirm that cash");
  });
});
