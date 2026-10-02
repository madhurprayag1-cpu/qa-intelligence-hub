"""Locust High-Concurrency Stress Testing Scenario for QA Intelligence Hub.

Adheres to AGENTS.md Section 8, 21, and 25:
- Simulates realistic synthetic passenger journeys across flight search, booking, ancillaries, and 3DS payment
- Evaluates throughput under concurrent virtual users (VU)
- Measures latency distributions across critical NDC workflows
"""

import json
import random
from locust import HttpUser, between, task


class AviationPassengerUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Initial user setup and airport resolution."""
        self.origins = ["ATH", "SKG", "HER", "JMK"]
        self.destinations = ["SKG", "ATH", "RHO", "CHQ"]
        self.current_flight_id = None
        self.current_booking_ref = None

    @task(5)
    def search_flights(self):
        """Frequent flight search query with origin/destination filters."""
        origin = random.choice(self.origins)
        dest = random.choice(self.destinations)
        while dest == origin:
            dest = random.choice(self.destinations)

        with self.client.get(
            f"/search/flights?origin={origin}&destination={dest}",
            name="/search/flights",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                flights = response.json()
                if flights:
                    self.current_flight_id = flights[0].get("id")
                response.success()
            else:
                response.failure(f"Flight search failed with status {response.status_code}")

    @task(3)
    def view_ancillary_catalog(self):
        """Retrieve dynamic ancillary baggage, meals, and seat selection options."""
        with self.client.get(
            "/bookings/ancillaries/catalog",
            name="/bookings/ancillaries/catalog",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Ancillary catalog failed: {response.status_code}")

    @task(2)
    def create_and_pay_booking(self):
        """Full transactional checkout: book seats and complete payment."""
        flight_id = self.current_flight_id or 1
        passenger_name = f"Test Passenger {random.randint(1000, 9999)}"
        passenger_email = f"pax_{random.randint(1000, 9999)}@example.com"

        booking_payload = {
            "flight_id": flight_id,
            "passenger_name": passenger_name,
            "passenger_email": passenger_email,
            "seats": random.randint(1, 2),
            "payment_method": "CREDIT_CARD",
            "ancillaries": {
                "baggage_id": "BAG_23KG",
                "seat_id": "SEAT_STANDARD",
            },
        }

        # 1. Create Booking
        with self.client.post(
            "/bookings",
            json=booking_payload,
            name="/bookings [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                booking_data = resp.json()
                self.current_booking_ref = booking_data.get("reference")
                resp.success()
            else:
                resp.failure(f"Booking creation failed: {resp.status_code}")
                return

        # 2. Process Payment
        if self.current_booking_ref:
            payment_payload = {
                "booking_reference": self.current_booking_ref,
                "amount": 185.00,
                "payment_method": "CREDIT_CARD",
                "card_last_four": "4242",
            }
            with self.client.post(
                "/payments",
                json=payment_payload,
                name="/payments [POST]",
                catch_response=True,
            ) as pay_resp:
                if pay_resp.status_code == 200:
                    pay_resp.success()
                else:
                    pay_resp.failure(f"Payment failed: {pay_resp.status_code}")

    @task(1)
    def evaluate_quality_gate_signal(self):
        """Invoke release quality gate evaluation."""
        payload = {
            "policy_name": "PRODUCTION_STRICT",
            "total_tests": 152,
            "passed_tests": 152,
            "failed_tests": 0,
            "critical_defects": 0,
            "contract_failures": 0,
            "rag_groundedness_score": 0.95,
        }
        with self.client.post(
            "/quality-gate/evaluate",
            json=payload,
            name="/quality-gate/evaluate [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Gate evaluation failed: {response.status_code}")
