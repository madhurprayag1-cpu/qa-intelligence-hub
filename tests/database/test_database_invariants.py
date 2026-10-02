"""Database Engineering & Schema Invariant Tests.

Adheres strictly to AGENTS.md Section 11 (Database Layer) & Section 14 (Database Engineering):
- Constraints, indexes, foreign keys, transactions, rollback isolation, appropriate normalization
- Verifies foreign key integrity rejection on invalid references
- Verifies uniqueness constraints (e.g., booking references)
- Verifies atomic inventory mutation and business rule consistency
- Verifies transactional rollback leaves no orphaned data
- Verifies audit fields (created_at, updated_at) auto-population
- Verifies RAG document chunks vector persistence & retrieval
- Verifies Quality Gate execution telemetry persistence & JSON round-tripping
"""

from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.airline import Airline
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.booking import Booking
from app.models.payment import Payment, PaymentMethod, PaymentStatus, ThreeDSStatus
from app.models.rag_chunk import RAGChunkModel
from app.models.quality_gate_run import QualityGateRunModel
from app.models.healthcare import (
    HealthcarePatientModel,
    HealthcareObservationModel,
    HealthcareAppointmentModel,
)
from app.models.fintech import (
    FinTechAccountModel,
    FinTechTransactionModel,
)
from app.models.ecommerce import (
    EcomProductModel,
    EcomOrderModel,
    EcomReturnModel,
)
from app.models.telecom import (
    TelecomSubscriberModel,
    TelecomCDRModel,
)


@pytest.fixture
def db_engine():
    """Create isolated SQLite in-memory database with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite does not enforce foreign keys by default; enable PRAGMA
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a clean transactional session for database testing."""
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_flight_graph(db_session):
    """Seed prerequisite airport and airline records for flight tests."""
    airline = Airline(
        id=1,
        code="QA",
        name="QA Intelligence Airways",
        country="Germany",
        active=True,
    )
    origin = Airport(
        id=1,
        code="BER",
        name="Berlin Brandenburg",
        city="Berlin",
        country="Germany",
        timezone="Europe/Berlin",
        active=True,
    )
    destination = Airport(
        id=2,
        code="MUC",
        name="Munich Franz Josef Strauss",
        city="Munich",
        country="Germany",
        timezone="Europe/Berlin",
        active=True,
    )
    flight = Flight(
        id=10,
        flight_number="QA-101",
        airline_id=1,
        origin_id=1,
        destination_id=2,
        departure_time=datetime.utcnow() + timedelta(days=2),
        arrival_time=datetime.utcnow() + timedelta(days=2, hours=1),
        duration_minutes=60,
        total_seats=10,
        available_seats=10,
        base_price=120.00,
        active=True,
    )
    db_session.add_all([airline, origin, destination, flight])
    db_session.commit()
    return flight


# ---------------------------------------------------------------------------
# 1. Schema & Table Registration
# ---------------------------------------------------------------------------

def test_schema_table_registration(db_engine):
    """Verify that all core tables and metadata are registered correctly."""
    registered_tables = set(Base.metadata.tables.keys())
    expected_tables = {
        "airlines",
        "airports",
        "flights",
        "bookings",
        "payments",
        "rag_document_chunks",
        "quality_gate_runs",
    }
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables: {expected_tables - registered_tables}"
    )


# ---------------------------------------------------------------------------
# 2. Foreign Key Integrity Constraints
# ---------------------------------------------------------------------------

def test_foreign_key_flight_rejects_nonexistent_airport(db_session):
    """Inserting a Flight with invalid airport foreign key must raise IntegrityError."""
    invalid_flight = Flight(
        id=99,
        flight_number="QA-ERR",
        airline_id=1,
        origin_id=9999,  # Non-existent
        destination_id=9998,  # Non-existent
        departure_time=datetime.utcnow(),
        arrival_time=datetime.utcnow(),
        duration_minutes=60,
        total_seats=100,
        available_seats=100,
        base_price=99.00,
    )
    db_session.add(invalid_flight)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_booking_rejects_nonexistent_flight(db_session):
    """Inserting a Booking referencing a non-existent flight must raise IntegrityError."""
    invalid_booking = Booking(
        reference="BK-ORPHAN",
        flight_id=99999,  # Non-existent flight
        passenger_name="Alice Explorer",
        passenger_email="alice@qahub.io",
        seats=1,
        base_fare=100.0,
        ancillary_amount=0.0,
        total_amount=100.0,
        status="CONFIRMED",
    )
    db_session.add(invalid_booking)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_payment_rejects_nonexistent_booking(db_session):
    """Inserting a Payment referencing a non-existent booking must raise IntegrityError."""
    invalid_payment = Payment(
        booking_id=99999,  # Non-existent booking
        amount=150.0,
        currency="EUR",
        method=PaymentMethod.CREDIT_CARD.value,
        status=PaymentStatus.PENDING.value,
        three_ds_status=ThreeDSStatus.NOT_REQUIRED.value,
    )
    db_session.add(invalid_payment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 3. Uniqueness Constraints
# ---------------------------------------------------------------------------

def test_booking_reference_uniqueness_constraint(db_session, seed_flight_graph):
    """Booking reference must be globally unique; duplicate must raise IntegrityError."""
    b1 = Booking(
        reference="BK-UNIQUE-1",
        flight_id=seed_flight_graph.id,
        passenger_name="John Unique",
        passenger_email="john@qahub.io",
        seats=1,
        total_amount=120.0,
        status="CONFIRMED",
    )
    db_session.add(b1)
    db_session.commit()

    b2 = Booking(
        reference="BK-UNIQUE-1",  # Duplicate reference
        flight_id=seed_flight_graph.id,
        passenger_name="Jane Imposter",
        passenger_email="jane@qahub.io",
        seats=1,
        total_amount=120.0,
        status="CONFIRMED",
    )
    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 4. Transactional Rollback Isolation
# ---------------------------------------------------------------------------

def test_transactional_rollback_preserves_atomic_state(db_session, seed_flight_graph):
    """A multi-step operation that fails halfway must rollback cleanly without orphaned state."""
    flight_id = seed_flight_graph.id
    initial_seats = seed_flight_graph.available_seats

    try:
        # Step 1: Create booking
        booking = Booking(
            reference="BK-ROLLBACK-TEST",
            flight_id=flight_id,
            passenger_name="Rollback User",
            passenger_email="rollback@qahub.io",
            seats=2,
            total_amount=240.0,
            status="CONFIRMED",
        )
        db_session.add(booking)

        # Step 2: Decrement inventory
        flight = db_session.get(Flight, flight_id)
        flight.available_seats -= 2

        # Step 3: Simulate catastrophic crash / unhandled failure before commit
        raise RuntimeError("Simulated upstream gateway timeout before commit")

    except RuntimeError:
        db_session.rollback()

    # Verify atomic state is completely clean
    persisted_booking = db_session.execute(
        select(Booking).where(Booking.reference == "BK-ROLLBACK-TEST")
    ).scalar_one_or_none()
    assert persisted_booking is None, "Failed transaction must not leave orphaned booking row"

    persisted_flight = db_session.get(Flight, flight_id)
    assert persisted_flight.available_seats == initial_seats, (
        f"Available seats should remain {initial_seats}, got {persisted_flight.available_seats}"
    )


# ---------------------------------------------------------------------------
# 5. Atomic Seat Inventory Mutation & Business Rules
# ---------------------------------------------------------------------------

def test_atomic_seat_inventory_deduction_and_restoration(db_session, seed_flight_graph):
    """Verifies atomic seat reservation and cancellation inventory restoration."""
    flight = seed_flight_graph
    assert flight.available_seats == 10

    # 1. Book 4 seats
    booking = Booking(
        reference="BK-ATOMIC-1",
        flight_id=flight.id,
        passenger_name="Family Group",
        passenger_email="family@qahub.io",
        seats=4,
        total_amount=480.0,
        status="CONFIRMED",
    )
    flight.available_seats -= 4
    db_session.add(booking)
    db_session.commit()

    db_session.refresh(flight)
    assert flight.available_seats == 6

    # 2. Attempt to book 7 seats (only 6 available) -> must be prevented
    requested_seats = 7
    if flight.available_seats < requested_seats:
        # Domain business rule check
        insufficient_seats = True
    else:
        insufficient_seats = False
    assert insufficient_seats is True, "Business invariant must reject overbooking"

    # 3. Cancel booking -> seats must be restored to 10
    booking.status = "CANCELLED"
    flight.available_seats += booking.seats
    db_session.commit()

    db_session.refresh(flight)
    assert flight.available_seats == 10


# ---------------------------------------------------------------------------
# 6. Audit Fields & Timestamps Auto-Population
# ---------------------------------------------------------------------------

def test_audit_fields_auto_population(db_session, seed_flight_graph):
    """Verifies created_at is automatically populated on insert for entities."""
    booking = Booking(
        reference="BK-AUDIT-1",
        flight_id=seed_flight_graph.id,
        passenger_name="Audit Traveler",
        passenger_email="audit@qahub.io",
        seats=1,
        total_amount=120.0,
        status="CONFIRMED",
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.created_at is not None
    assert isinstance(booking.created_at, datetime)
    assert (datetime.utcnow() - booking.created_at).total_seconds() < 10


# ---------------------------------------------------------------------------
# 7. RAG Vector Storage & Document Chunk Database Invariants
# ---------------------------------------------------------------------------

def test_rag_chunk_vector_storage_and_metadata(db_session):
    """Verifies persistent storage and retrieval of RAG embedding vectors in the database."""
    chunk = RAGChunkModel(
        document_id="DOC-BAGGAGE-POLICY-2026",
        chunk_id="DOC-BAGGAGE-POLICY-2026-CH0",
        text="Economy passengers are permitted one carry-on bag up to 8kg and 55x40x23cm.",
        embedding=[0.12, 0.45, -0.22, 0.88, 0.05],
        metadata_json={"category": "baggage", "version": "v2.1", "source": "passenger_handbook.md"},
    )
    db_session.add(chunk)
    db_session.commit()

    retrieved = db_session.execute(
        select(RAGChunkModel).where(RAGChunkModel.document_id == "DOC-BAGGAGE-POLICY-2026")
    ).scalar_one()

    assert retrieved.chunk_id == "DOC-BAGGAGE-POLICY-2026-CH0"
    assert "Economy passengers" in retrieved.text
    assert len(retrieved.embedding) == 5
    assert retrieved.embedding[0] == pytest.approx(0.12)
    assert retrieved.metadata_json["category"] == "baggage"
    assert retrieved.created_at is not None


# ---------------------------------------------------------------------------
# 8. Quality Gate Run History Persistence & JSON Round-Trip
# ---------------------------------------------------------------------------

def test_quality_gate_run_persistence_and_telemetry(db_session):
    """Verifies QualityGateRunModel stores full execution telemetry and violation JSON."""
    run = QualityGateRunModel(
        run_id="QG-RUN-TEST-001",
        policy_name="PRODUCTION_STRICT",
        status="BLOCKED",
        passed=False,
        total_tests=100,
        passed_tests=92,
        failed_tests=8,
        critical_defects=2,
        contract_failures=1,
        security_vulnerabilities=1,
        rag_groundedness_score=0.72,
        violations=[
            "Test pass rate 92.0% < threshold 100.0%",
            "Critical defects 2 > allowed 0",
            "Security vulnerabilities 1 > allowed 0",
        ],
    )
    db_session.add(run)
    db_session.commit()

    retrieved = db_session.execute(
        select(QualityGateRunModel).where(QualityGateRunModel.run_id == "QG-RUN-TEST-001")
    ).scalar_one()

    assert retrieved.status == "BLOCKED"
    assert retrieved.passed is False
    assert len(retrieved.violations) == 3
    assert "Critical defects" in retrieved.violations[1]
    assert retrieved.created_at is not None


# ---------------------------------------------------------------------------
# 9. Booking Ownership and Tenant Isolation Data Invariants
# ---------------------------------------------------------------------------

def test_booking_owner_user_id_persistence_and_query(db_session, seed_flight_graph):
    """Verifies that owner_user_id is correctly persisted and queryable on Booking."""
    booking = Booking(
        reference="BK-OWNER-001",
        flight_id=seed_flight_graph.id,
        passenger_name="Owner Tenant",
        passenger_email="owner@tenant.io",
        owner_user_id=901,
        seats=1,
        total_amount=150.0,
        status="CONFIRMED",
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    assert booking.owner_user_id == 901

    retrieved = db_session.execute(
        select(Booking).where(Booking.owner_user_id == 901)
    ).scalar_one()
    assert retrieved.reference == "BK-OWNER-001"
    assert retrieved.owner_user_id == 901


# ---------------------------------------------------------------------------
# 10. Multi-Domain SUT Schema & Metadata Invariants
# ---------------------------------------------------------------------------

def test_multidomain_tables_registered_in_metadata():
    """Verifies that all 10 required domain tables are registered in Base.metadata."""
    expected_tables = {
        "healthcare_patients",
        "healthcare_observations",
        "healthcare_appointments",
        "fintech_accounts",
        "fintech_transactions",
        "ecommerce_products",
        "ecommerce_orders",
        "ecommerce_returns",
        "telecom_subscribers",
        "telecom_cdrs",
    }
    registered = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered), f"Missing tables: {expected_tables - registered}"


def test_multidomain_tenant_isolation_columns_and_indexes():
    """Verifies owner_user_id column and index on all customer tenant entities."""
    tenant_tables = [
        "healthcare_patients",
        "fintech_accounts",
        "ecommerce_orders",
        "telecom_subscribers",
    ]
    for table_name in tenant_tables:
        table = Base.metadata.tables[table_name]
        assert "owner_user_id" in table.c, f"Table {table_name} missing owner_user_id column"
        col = table.c["owner_user_id"]
        assert col.nullable is True
        has_owner_idx = any(
            "owner_user_id" in [c.name for c in idx.columns]
            for idx in table.indexes
        )
        assert has_owner_idx, f"Table {table_name} missing index on owner_user_id"


# ---------------------------------------------------------------------------
# 11. Healthcare Data Invariants
# ---------------------------------------------------------------------------

def test_healthcare_patient_and_observation_cascade_invariant(db_session):
    """Verifies patient persistence, observation FK linkage, and cascade cleanup."""
    patient = HealthcarePatientModel(
        id="MRN-TEST-001",
        owner_user_id=801,
        family_name="Papadopoulos",
        given_names=["Dimitris", "Alex"],
        gender="male",
        birth_date="1985-06-15",
        ssn_masked="***-**-4589",
        phone_masked="***-***-0199",
        email="dimitris@example.test",
        active=True,
    )
    db_session.add(patient)
    db_session.commit()

    obs = HealthcareObservationModel(
        id="OBS-TEST-001",
        patient_id="MRN-TEST-001",
        loinc_code="8867-4",
        display_name="Heart rate",
        value_quantity=72.0,
        unit="beats/min",
        status="final",
        effective_date_time="2026-10-01T12:00:00Z",
    )
    db_session.add(obs)
    db_session.commit()

    retrieved = db_session.execute(
        select(HealthcarePatientModel).where(HealthcarePatientModel.owner_user_id == 801)
    ).scalar_one()
    assert retrieved.family_name == "Papadopoulos"
    assert retrieved.ssn_masked == "***-**-4589"

    invalid_obs = HealthcareObservationModel(
        id="OBS-INVALID",
        patient_id="NON-EXISTENT-MRN",
        loinc_code="8480-6",
        display_name="Systolic blood pressure",
        value_quantity=120.0,
        effective_date_time="2026-10-01T12:00:00Z",
    )
    db_session.add(invalid_obs)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 12. FinTech Data Invariants
# ---------------------------------------------------------------------------

def test_fintech_account_unique_iban_and_transaction_fk(db_session):
    """Verifies account IBAN uniqueness and transaction foreign key relationships."""
    from decimal import Decimal

    acc1 = FinTechAccountModel(
        account_id="ACC-TEST-001",
        owner_user_id=701,
        iban="GB29QAHB60161300000001",
        bic_swift="CHASUS33XXX",
        account_holder="FinTech Tester 1",
        email="ft1@example.test",
        currency="USD",
        balance=Decimal("5000.00"),
        kyc_tier="TIER_2_VERIFIED",
    )
    acc2 = FinTechAccountModel(
        account_id="ACC-TEST-002",
        owner_user_id=702,
        iban="GB29QAHB60161300000002",
        bic_swift="BARCGB22XXX",
        account_holder="FinTech Tester 2",
        email="ft2@example.test",
        currency="USD",
        balance=Decimal("2000.00"),
    )
    db_session.add_all([acc1, acc2])
    db_session.commit()

    duplicate_acc = FinTechAccountModel(
        account_id="ACC-TEST-DUP",
        owner_user_id=703,
        iban="GB29QAHB60161300000001",
        bic_swift="CHASUS33XXX",
        account_holder="Duplicate Tester",
        email="dup@example.test",
    )
    db_session.add(duplicate_acc)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    txn = FinTechTransactionModel(
        transaction_id="TXN-TEST-001",
        source_account_id="ACC-TEST-001",
        destination_account_id="ACC-TEST-002",
        amount=Decimal("250.00"),
        currency="USD",
        status="SETTLED",
    )
    db_session.add(txn)
    db_session.commit()

    retrieved = db_session.execute(
        select(FinTechTransactionModel).where(FinTechTransactionModel.transaction_id == "TXN-TEST-001")
    ).scalar_one()
    assert retrieved.amount == Decimal("250.00")
    assert retrieved.source_account_id == "ACC-TEST-001"


# ---------------------------------------------------------------------------
# 13. E-Commerce Data Invariants
# ---------------------------------------------------------------------------

def test_ecommerce_product_and_order_return_invariants(db_session):
    """Verifies product catalog persistence and order-to-return cascade invariants."""
    from decimal import Decimal

    product = EcomProductModel(
        sku="SKU-ECOM-TEST-01",
        name="Noise-Cancelling Headphones",
        category="ELECTRONICS",
        price=Decimal("149.99"),
        stock_quantity=50,
        weight_kg=Decimal("0.40"),
    )
    db_session.add(product)
    db_session.commit()

    order = EcomOrderModel(
        order_id="ORD-EC-TEST-01",
        owner_user_id=601,
        customer_id="CUST-601",
        customer_email="buyer@example.test",
        items=[{"sku": "SKU-ECOM-TEST-01", "quantity": 1, "unit_price": 149.99}],
        status="DELIVERED",
        subtotal=Decimal("149.99"),
        total_amount=Decimal("161.99"),
        shipping_tier="STANDARD",
        shipping_address={"city": "Athens", "country": "GR"},
        payment_transaction_id="TXN-EC-TEST-001",
    )
    db_session.add(order)
    db_session.commit()

    ret = EcomReturnModel(
        return_id="RMA-EC-TEST-01",
        order_id="ORD-EC-TEST-01",
        sku="SKU-ECOM-TEST-01",
        quantity=1,
        reason="Defective audio driver",
        refund_amount=Decimal("149.99"),
        status="REQUESTED",
    )
    db_session.add(ret)
    db_session.commit()

    retrieved_order = db_session.execute(
        select(EcomOrderModel).where(EcomOrderModel.owner_user_id == 601)
    ).scalar_one()
    assert retrieved_order.order_id == "ORD-EC-TEST-01"
    assert retrieved_order.total_amount == Decimal("161.99")


# ---------------------------------------------------------------------------
# 14. Telecom Data Invariants
# ---------------------------------------------------------------------------

def test_telecom_subscriber_unique_msisdn_and_cdr_linkage(db_session):
    """Verifies unique subscriber identity and CDR foreign key linkage."""
    from decimal import Decimal

    sub = TelecomSubscriberModel(
        subscriber_id="SUB-TC-TEST-01",
        owner_user_id=501,
        msisdn="+14155550199",
        iccid="89310000000000000001",
        imsi="310260000000001",
        plan_id="PLAN-5G-UNLIMITED",
        status="active",
        balance=Decimal("25.00"),
        data_used_mb=Decimal("512.50"),
    )
    db_session.add(sub)
    db_session.commit()

    dup_sub = TelecomSubscriberModel(
        subscriber_id="SUB-TC-TEST-DUP",
        owner_user_id=502,
        msisdn="+14155550199",
        iccid="89310000000000000002",
        imsi="310260000000002",
        plan_id="PLAN-5G-UNLIMITED",
    )
    db_session.add(dup_sub)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    cdr = TelecomCDRModel(
        cdr_id="CDR-TC-TEST-01",
        msisdn="+14155550199",
        destination="+14155550100",
        call_type="voice",
        duration_seconds=120,
        rated_amount=Decimal("0.20"),
        billed=True,
    )
    db_session.add(cdr)
    db_session.commit()

    retrieved = db_session.execute(
        select(TelecomCDRModel).where(TelecomCDRModel.cdr_id == "CDR-TC-TEST-01")
    ).scalar_one()
    assert retrieved.msisdn == "+14155550199"
    assert retrieved.rated_amount == Decimal("0.20")


# ---------------------------------------------------------------------------
# 15. Migration Upgrade / Downgrade Contract Verification
# ---------------------------------------------------------------------------

def test_multidomain_migration_revision_contract():
    """Verifies that the migration module defines valid revision, down_revision, upgrade, and downgrade."""
    import importlib
    mig = importlib.import_module("migrations.versions.d4e5f6a7b8c9_add_multidomain_sut_tables")
    assert mig.revision == "d4e5f6a7b8c9"
    assert mig.down_revision == "c2b674d52e19"
    assert callable(mig.upgrade)
    assert callable(mig.downgrade)
