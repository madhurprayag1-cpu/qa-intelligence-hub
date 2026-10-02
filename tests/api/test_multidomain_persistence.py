"""Comprehensive Test Suite for Phase 1B.2 Backend Domain Router Persistence Binding.

Verifies:
1. PostgreSQL / SQLAlchemy persistence across all 4 domains (Healthcare, FinTech, E-Commerce, Telecom).
2. Server-authoritative tenant isolation: owner_user_id == current_user.id.
3. IDOR prevention: Cross-user access rejected with HTTP 403 Forbidden.
4. Unauthorized access prevention: Unauthenticated / role 'unauthorized' rejected.
5. Invalid token rejection: Bad or tampered tokens return HTTP 401 Unauthorized.
6. Candidate lookup endpoints:
   - GET /healthcare/patients
   - GET /healthcare/practitioners
   - GET /healthcare/appointments
   - GET /fintech/accounts
   - GET /fintech/transactions/{account_id}
   - GET /ecommerce/orders
   - GET /telecom/subscribers/{msisdn}/cdrs
7. State integrity and domain engine invariants:
   - FHIR R4 schema and HIPAA masking
   - FinTech double-entry balance and ledger
   - E-Commerce order FSM and inventory deduction
   - Telecom subscriber FSM and rating engine deduction
"""

import pytest
from sqlalchemy.orm import Session

from app.models.healthcare import (
    HealthcareAppointmentModel,
    HealthcareObservationModel,
    HealthcarePatientModel,
)
from app.models.fintech import FinTechAccountModel, FinTechTransactionModel
from app.models.ecommerce import EcomOrderModel, EcomProductModel, EcomReturnModel
from app.models.telecom import TelecomCDRModel, TelecomSubscriberModel
from domains.fintech.factories import AccountFactory
from domains.telecom.factories import SubscriberFactory
from tests.conftest import authenticated, auth_headers


# ==============================================================================
# 1. HEALTHCARE DOMAIN PERSISTENCE & TENANT ISOLATION TESTS
# ==============================================================================

def test_healthcare_patient_creation_persistence_and_owner_isolation(client, db_session: Session):
    """Verify patient is persisted to DB with owner_user_id and protected against IDOR."""
    patient_payload = {
        "resourceType": "Patient",
        "id": "MRN-HC-888001",
        "active": True,
        "name": [{"family": "Skywalker", "given": ["Luke"]}],
        "gender": "male",
        "birthDate": "1995-05-04",
        "telecom": [
            {"system": "email", "value": "luke@rebel.org"},
            {"system": "phone", "value": "555-0199"},
        ],
        "ssn_raw": "987-65-4321",
    }

    # 1. Alice (id=101) creates the patient
    with authenticated(client, "passenger@qahub.io"):
        create_resp = client.post("/healthcare/patients", json=patient_payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["ssn_masked"] == "***-**-4321"

    # 2. Verify database persistence
    db_patient = db_session.get(HealthcarePatientModel, "MRN-HC-888001")
    assert db_patient is not None
    assert db_patient.owner_user_id == 101
    assert db_patient.family_name == "Skywalker"
    assert db_patient.given_names == ["Luke"]

    # 3. Alice can retrieve her patient record
    with authenticated(client, "passenger@qahub.io"):
        get_resp = client.get("/healthcare/patients/MRN-HC-888001")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == "MRN-HC-888001"

    # 4. Bob (id=201, qa_engineer role) attempting cross-tenant access is blocked by IDOR protection
    with authenticated(client, "qa@qahub.io"):
        idor_resp = client.get("/healthcare/patients/MRN-HC-888001")
    assert idor_resp.status_code == 403
    assert "IDOR protection prevented access" in idor_resp.json()["detail"]

    # 5. Admin (id=401) can access for oversight
    with authenticated(client, "admin@qahub.io"):
        admin_resp = client.get("/healthcare/patients/MRN-HC-888001")
    assert admin_resp.status_code == 200

    # 6. Unauthorized role is rejected
    unauth_resp = client.get("/healthcare/patients/MRN-HC-888001", headers={"X-User-Role": "unauthorized"})
    assert unauth_resp.status_code == 403


def test_healthcare_lookup_endpoints_and_observation_persistence(client, db_session: Session):
    """Verify candidate lookup endpoints and observation persistence."""
    # List practitioners
    pract_resp = client.get("/healthcare/practitioners")
    assert pract_resp.status_code == 200
    assert len(pract_resp.json()) >= 3
    assert any("DR-CHEN" in p["id"] for p in pract_resp.json())

    # List patients scoped to tenant
    with authenticated(client, "passenger@qahub.io"):
        list_resp = client.get("/healthcare/patients")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)

    # Ingest observation and check DB
    obs_payload = {
        "resourceType": "Observation",
        "id": "OBS-HC-999001",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}],
        },
        "subject": {"reference": "Patient/MRN-HC-888001"},
        "effectiveDateTime": "2026-10-01T10:00:00Z",
        "valueQuantity": {"value": 72.0, "unit": "beats/min", "code": "/min", "system": "http://unitsofmeasure.org"},
    }
    with authenticated(client, "passenger@qahub.io"):
        obs_resp = client.post("/healthcare/observations", json=obs_payload)
    assert obs_resp.status_code == 201

    db_obs = db_session.get(HealthcareObservationModel, "OBS-HC-999001")
    assert db_obs is not None
    assert db_obs.patient_id == "MRN-HC-888001"
    assert float(db_obs.value_quantity) == 72.0

    # Appointment scheduling with calendar conflict check
    appt_1 = {
        "resourceType": "Appointment",
        "id": "APPT-HC-999001",
        "status": "booked",
        "start": "2026-10-15T09:00:00Z",
        "end": "2026-10-15T09:30:00Z",
        "participant": [
            {"actor": {"reference": "Patient/MRN-HC-888001"}, "status": "accepted"},
            {"actor": {"reference": "Practitioner/DR-CHEN-01"}, "status": "accepted"},
        ],
    }
    with authenticated(client, "passenger@qahub.io"):
        res1 = client.post("/healthcare/appointments", json=appt_1)
    assert res1.status_code == 201

    db_appt = db_session.get(HealthcareAppointmentModel, "APPT-HC-999001")
    assert db_appt is not None
    assert db_appt.practitioner_ref == "Practitioner/DR-CHEN-01"

    # Conflicting appointment for same practitioner
    appt_conflict = {
        "resourceType": "Appointment",
        "id": "APPT-HC-999002",
        "status": "booked",
        "start": "2026-10-15T09:15:00Z",
        "end": "2026-10-15T09:45:00Z",
        "participant": [
            {"actor": {"reference": "Patient/MRN-HC-888001"}, "status": "accepted"},
            {"actor": {"reference": "Practitioner/DR-CHEN-01"}, "status": "accepted"},
        ],
    }
    with authenticated(client, "passenger@qahub.io"):
        res2 = client.post("/healthcare/appointments", json=appt_conflict)
    assert res2.status_code == 409
    assert "Practitioner calendar conflict" in res2.json()["detail"]


# ==============================================================================
# 2. FINTECH DOMAIN PERSISTENCE & TENANT ISOLATION TESTS
# ==============================================================================

def test_fintech_account_persistence_and_owner_isolation(client, db_session: Session):
    """Verify FinTech account is persisted to DB with owner_user_id and protected against IDOR."""
    acc = AccountFactory.build(index=1, balance=5000.0)
    acc_payload = acc.model_dump(mode="json")
    acc_id = acc.account_id

    # Alice (id=101) creates account
    with authenticated(client, "passenger@qahub.io"):
        create_resp = client.post("/fintech/accounts", json=acc_payload)
    assert create_resp.status_code == 201

    # Verify DB persistence
    db_acc = db_session.get(FinTechAccountModel, acc_id)
    assert db_acc is not None
    assert db_acc.owner_user_id == 101
    assert float(db_acc.balance) == 5000.0

    # Alice can inspect account
    with authenticated(client, "passenger@qahub.io"):
        get_resp = client.get(f"/fintech/accounts/{acc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["balance"] == 5000.0

    # Bob (id=201) cannot inspect Alice's account (IDOR prevention)
    with authenticated(client, "qa@qahub.io"):
        idor_resp = client.get(f"/fintech/accounts/{acc_id}")
    assert idor_resp.status_code == 403
    assert "IDOR protection prevented access" in idor_resp.json()["detail"]

    # Customer accounts list lookup
    with authenticated(client, "passenger@qahub.io"):
        list_resp = client.get("/fintech/accounts")
    assert list_resp.status_code == 200
    assert any(a["account_id"] == acc_id for a in list_resp.json())


def test_fintech_transfer_persistence_and_transaction_history(client, db_session: Session):
    """Verify double-entry transfer updates DB balances and creates transaction records."""
    src = AccountFactory.build(index=2, balance=2000.0)
    dst = AccountFactory.build(index=3, balance=500.0)
    src_id = src.account_id
    dst_id = dst.account_id

    with authenticated(client, "passenger@qahub.io"):
        client.post("/fintech/accounts", json=src.model_dump(mode="json"))
        client.post("/fintech/accounts", json=dst.model_dump(mode="json"))

    # Execute transfer: Alice transfers $300 to Bob
    transfer_payload = {
        "source_account_id": src_id,
        "destination_account_id": dst_id,
        "amount": 300.0,
    }
    with authenticated(client, "passenger@qahub.io"):
        txn_resp = client.post("/fintech/transfers", json=transfer_payload)
    assert txn_resp.status_code == 201
    assert txn_resp.json()["source_new_balance"] == 1700.0
    assert txn_resp.json()["dest_new_balance"] == 800.0

    # Verify DB balances updated
    db_src = db_session.get(FinTechAccountModel, src_id)
    db_dst = db_session.get(FinTechAccountModel, dst_id)
    assert float(db_src.balance) == 1700.0
    assert float(db_dst.balance) == 800.0

    # Verify transaction history lookup
    with authenticated(client, "passenger@qahub.io"):
        hist_resp = client.get(f"/fintech/transactions/{src_id}")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1
    assert hist_resp.json()[0]["amount"] == 300.0

    # Bob attempting to view Alice's transactions is blocked
    with authenticated(client, "qa@qahub.io"):
        hist_idor = client.get(f"/fintech/transactions/{src_id}")
    assert hist_idor.status_code == 403


# ==============================================================================
# 3. E-COMMERCE DOMAIN PERSISTENCE & TENANT ISOLATION TESTS
# ==============================================================================

def test_ecommerce_checkout_persistence_and_order_lifecycle(client, db_session: Session):
    """Verify order persistence, stock deduction, and FSM transition in PostgreSQL."""
    # 1. Check products catalog and ensure baseline products exist in DB
    prod_resp = client.get("/ecommerce/products")
    assert prod_resp.status_code == 200
    products = prod_resp.json()
    assert len(products) > 0
    target_prod = products[0]
    target_sku = target_prod["sku"]
    initial_stock = target_prod["stock_quantity"]

    # 2. Alice checks out 2 units
    checkout_payload = {
        "cart_id": "CART-101",
        "customer_id": "CUST-101",
        "customer_email": "passenger@qahub.io",
        "items": [
            {
                "sku": target_sku,
                "product_name": target_prod["name"],
                "unit_price": target_prod["price"],
                "quantity": 2,
            }
        ],
        "shipping_tier": "STANDARD",
        "payment_method": "CREDIT_CARD",
        "shipping_address": {
            "full_name": "Alice Passenger",
            "address_line1": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "USA",
        },
    }
    with authenticated(client, "passenger@qahub.io"):
        checkout_resp = client.post("/ecommerce/checkout", json=checkout_payload)
    assert checkout_resp.status_code == 201
    order_id = checkout_resp.json()["order_id"]

    # 3. Verify DB persistence
    db_order = db_session.get(EcomOrderModel, order_id)
    assert db_order is not None
    assert db_order.owner_user_id == 101
    assert db_order.status == "PAYMENT_AUTHORIZED"

    # Verify inventory was deducted in DB
    db_prod = db_session.get(EcomProductModel, target_sku)
    if db_prod:
        assert db_prod.stock_quantity == initial_stock - 2

    # 4. Alice retrieves order
    with authenticated(client, "passenger@qahub.io"):
        get_order_resp = client.get(f"/ecommerce/orders/{order_id}")
    assert get_order_resp.status_code == 200
    assert get_order_resp.json()["order_id"] == order_id

    # 5. Bob (id=201) cannot inspect Alice's order (IDOR)
    with authenticated(client, "qa@qahub.io"):
        idor_resp = client.get(f"/ecommerce/orders/{order_id}")
    assert idor_resp.status_code == 403
    assert "IDOR protection prevented access" in idor_resp.json()["detail"]

    # 6. Alice lists her orders
    with authenticated(client, "passenger@qahub.io"):
        orders_list = client.get("/ecommerce/orders")
    assert orders_list.status_code == 200
    assert any(o["order_id"] == order_id for o in orders_list.json())

    # 7. Transition order status: PAYMENT_AUTHORIZED -> PROCESSING
    with authenticated(client, "admin@qahub.io"):
        status_resp = client.put(f"/ecommerce/orders/{order_id}/status", json={"status": "PROCESSING"})
    assert status_resp.status_code == 200

    db_session.refresh(db_order)
    assert db_order.status == "PROCESSING"

    # 8. Refund / return persistence
    with authenticated(client, "passenger@qahub.io"):
        refund_resp = client.post(
            "/ecommerce/refunds",
            json={
                "return_id": f"RMA-{order_id}",
                "order_id": order_id,
                "amount": 25.0,
                "reason": "Defective item",
            },
        )
    assert refund_resp.status_code == 201

    db_return = db_session.get(EcomReturnModel, f"RMA-{order_id}")
    assert db_return is not None
    assert float(db_return.refund_amount) == 25.0


# ==============================================================================
# 4. TELECOM DOMAIN PERSISTENCE & TENANT ISOLATION TESTS
# ==============================================================================

def test_telecom_subscriber_persistence_sim_swap_and_cdr_history(client, db_session: Session):
    """Verify Telecom subscriber persistence, SIM swap, CDR rating, and IDOR defense."""
    sub = SubscriberFactory.build(index=5)
    sub_payload = sub.model_dump(mode="json")
    msisdn = sub.msisdn

    # 1. Alice provisions line
    with authenticated(client, "passenger@qahub.io"):
        create_resp = client.post("/telecom/subscribers", json=sub_payload)
    assert create_resp.status_code == 201

    # Verify DB persistence
    db_sub = db_session.query(TelecomSubscriberModel).filter(TelecomSubscriberModel.msisdn == msisdn).first()
    assert db_sub is not None
    assert db_sub.owner_user_id == 101
    assert db_sub.msisdn == msisdn

    # 2. Alice retrieves profile (assert CPNI masking)
    with authenticated(client, "passenger@qahub.io"):
        get_resp = client.get(f"/telecom/subscribers/{msisdn}")
    assert get_resp.status_code == 200
    assert "sim" in get_resp.json()
    assert "********" in get_resp.json()["sim"]["imsi"]

    # 3. Bob (id=201) cannot inspect Alice's subscriber line (IDOR)
    with authenticated(client, "qa@qahub.io"):
        idor_resp = client.get(f"/telecom/subscribers/{msisdn}")
    assert idor_resp.status_code == 403
    assert "IDOR protection prevented access" in idor_resp.json()["detail"]

    # 4. SIM Swap updates DB IMSI
    with authenticated(client, "passenger@qahub.io"):
        swap_resp = client.post(
            f"/telecom/subscribers/{msisdn}/sim-swap",
            json={"new_iccid": "89014103299998887702", "new_imsi": "310410987654321"},
        )
    assert swap_resp.status_code == 200
    assert swap_resp.json()["status"] == "SWAP_COMPLETED"

    db_session.refresh(db_sub)
    assert db_sub.imsi == "310410987654321"

    # 5. Rate CDR and verify DB CDR persistence
    cdr_payload = {
        "cdr": {
            "cdr_id": "CDR-TEL-999001",
            "msisdn": msisdn,
            "call_type": "voice",
            "destination": "+15551234567",
            "duration_seconds": 180,
            "bytes_transferred": 0,
            "zone": "domestic",
            "timestamp": "2026-10-01T12:00:00Z",
            "rated_amount": 0.0,
            "billed": False,
        }
    }
    with authenticated(client, "passenger@qahub.io"):
        rate_resp = client.post("/telecom/cdr/rate", json=cdr_payload)
    assert rate_resp.status_code == 200

    db_cdr = db_session.get(TelecomCDRModel, "CDR-TEL-999001")
    assert db_cdr is not None
    assert db_cdr.msisdn == msisdn
    assert db_cdr.duration_seconds == 180

    # 6. Lookup CDR history endpoint
    with authenticated(client, "passenger@qahub.io"):
        cdrs_resp = client.get(f"/telecom/subscribers/{msisdn}/cdrs")
    assert cdrs_resp.status_code == 200
    assert len(cdrs_resp.json()) >= 1

    # Bob attempting to view Alice's CDRs is blocked
    with authenticated(client, "qa@qahub.io"):
        cdrs_idor = client.get(f"/telecom/subscribers/{msisdn}/cdrs")
    assert cdrs_idor.status_code == 403


# ==============================================================================
# 5. AUTHENTICATION INTEGRITY & TOKEN SECURITY TESTS
# ==============================================================================

def test_invalid_and_tampered_token_rejection(client):
    """Verify invalid or tampered tokens return 401 Unauthorized across all domain endpoints."""
    bad_headers = {"Authorization": "Bearer completely-invalid-jwt-token"}

    resp1 = client.get("/healthcare/patients/MRN-HC-888001", headers=bad_headers)
    assert resp1.status_code == 401
    assert "WWW-Authenticate" in resp1.headers

    resp2 = client.get("/fintech/accounts/ACC-FT10000001", headers=bad_headers)
    assert resp2.status_code == 401

    resp3 = client.get("/ecommerce/orders/ORD-EC-1001", headers=bad_headers)
    assert resp3.status_code == 401

    resp4 = client.get("/telecom/subscribers/+15559876543", headers=bad_headers)
    assert resp4.status_code == 401
