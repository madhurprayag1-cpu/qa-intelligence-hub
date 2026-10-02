"""add multidomain sut tables

Revision ID: d4e5f6a7b8c9
Revises: c2b674d52e19
Create Date: 2026-10-01 13:10:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2b674d52e19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Healthcare Domain Tables
    # ---------------------------------------------------------
    op.create_table(
        "healthcare_patients",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("family_name", sa.String(length=100), nullable=False),
        sa.Column("given_names", sa.JSON(), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=False),
        sa.Column("birth_date", sa.String(length=10), nullable=False),
        sa.Column("ssn_masked", sa.String(length=20), nullable=True),
        sa.Column("phone_masked", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_healthcare_patients_owner_user_id", "healthcare_patients", ["owner_user_id"])

    op.create_table(
        "healthcare_observations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(length=64),
            sa.ForeignKey("healthcare_patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("loinc_code", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("value_quantity", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="final"),
        sa.Column("effective_date_time", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_healthcare_observations_patient_id", "healthcare_observations", ["patient_id"])
    op.create_index("ix_healthcare_observations_loinc_code", "healthcare_observations", ["loinc_code"])

    op.create_table(
        "healthcare_appointments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(length=64),
            sa.ForeignKey("healthcare_patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("practitioner_ref", sa.String(length=100), nullable=False),
        sa.Column("service_type", sa.String(length=100), nullable=True),
        sa.Column("start_time", sa.String(length=50), nullable=False),
        sa.Column("end_time", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="booked"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_healthcare_appointments_patient_id", "healthcare_appointments", ["patient_id"])
    op.create_index("ix_healthcare_appointments_practitioner_ref", "healthcare_appointments", ["practitioner_ref"])
    op.create_index("ix_healthcare_appointments_start_time", "healthcare_appointments", ["start_time"])
    op.create_index("ix_healthcare_appointments_status", "healthcare_appointments", ["status"])

    # ---------------------------------------------------------
    # 2. FinTech Domain Tables
    # ---------------------------------------------------------
    op.create_table(
        "fintech_accounts",
        sa.Column("account_id", sa.String(length=32), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("iban", sa.String(length=34), unique=True, nullable=False),
        sa.Column("bic_swift", sa.String(length=11), nullable=False),
        sa.Column("account_holder", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=30), nullable=False, server_default="CHECKING"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("balance", sa.Numeric(precision=14, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("kyc_tier", sa.String(length=30), nullable=False, server_default="TIER_2_VERIFIED"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fintech_accounts_owner_user_id", "fintech_accounts", ["owner_user_id"])
    op.create_index("ix_fintech_accounts_iban", "fintech_accounts", ["iban"])

    op.create_table(
        "fintech_transactions",
        sa.Column("transaction_id", sa.String(length=32), primary_key=True),
        sa.Column(
            "source_account_id",
            sa.String(length=32),
            sa.ForeignKey("fintech_accounts.account_id"),
            nullable=False,
        ),
        sa.Column(
            "destination_account_id",
            sa.String(length=32),
            sa.ForeignKey("fintech_accounts.account_id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="SETTLED"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fintech_transactions_source_account_id", "fintech_transactions", ["source_account_id"])
    op.create_index("ix_fintech_transactions_destination_account_id", "fintech_transactions", ["destination_account_id"])
    op.create_index("ix_fintech_transactions_status", "fintech_transactions", ["status"])

    # ---------------------------------------------------------
    # 3. E-Commerce Domain Tables
    # ---------------------------------------------------------
    op.create_table(
        "ecommerce_products",
        sa.Column("sku", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.50")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ecommerce_products_category", "ecommerce_products", ["category"])

    op.create_table(
        "ecommerce_orders",
        sa.Column("order_id", sa.String(length=32), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.String(length=64), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PAYMENT_AUTHORIZED"),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("shipping_cost", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("shipping_tier", sa.String(length=30), nullable=False, server_default="STANDARD"),
        sa.Column("shipping_address", sa.JSON(), nullable=False),
        sa.Column("payment_transaction_id", sa.String(length=64), nullable=False),
        sa.Column("tracking_number", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ecommerce_orders_owner_user_id", "ecommerce_orders", ["owner_user_id"])
    op.create_index("ix_ecommerce_orders_customer_id", "ecommerce_orders", ["customer_id"])
    op.create_index("ix_ecommerce_orders_status", "ecommerce_orders", ["status"])

    op.create_table(
        "ecommerce_returns",
        sa.Column("return_id", sa.String(length=32), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(length=32),
            sa.ForeignKey("ecommerce_orders.order_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("refund_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="REQUESTED"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ecommerce_returns_order_id", "ecommerce_returns", ["order_id"])
    op.create_index("ix_ecommerce_returns_status", "ecommerce_returns", ["status"])

    # ---------------------------------------------------------
    # 4. Telecom Domain Tables
    # ---------------------------------------------------------
    op.create_table(
        "telecom_subscribers",
        sa.Column("subscriber_id", sa.String(length=32), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("msisdn", sa.String(length=20), unique=True, nullable=False),
        sa.Column("iccid", sa.String(length=24), unique=True, nullable=False),
        sa.Column("imsi", sa.String(length=15), unique=True, nullable=False),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("balance", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("minutes_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sms_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("data_used_mb", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("roaming_allowed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("kyc_verified", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_telecom_subscribers_owner_user_id", "telecom_subscribers", ["owner_user_id"])
    op.create_index("ix_telecom_subscribers_msisdn", "telecom_subscribers", ["msisdn"])
    op.create_index("ix_telecom_subscribers_iccid", "telecom_subscribers", ["iccid"])
    op.create_index("ix_telecom_subscribers_imsi", "telecom_subscribers", ["imsi"])
    op.create_index("ix_telecom_subscribers_plan_id", "telecom_subscribers", ["plan_id"])
    op.create_index("ix_telecom_subscribers_status", "telecom_subscribers", ["status"])

    op.create_table(
        "telecom_cdrs",
        sa.Column("cdr_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "msisdn",
            sa.String(length=20),
            sa.ForeignKey("telecom_subscribers.msisdn", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=50), nullable=False),
        sa.Column("call_type", sa.String(length=30), nullable=False),
        sa.Column("zone", sa.String(length=30), nullable=False, server_default="domestic"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("bytes_transferred", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rated_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("billed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_telecom_cdrs_msisdn", "telecom_cdrs", ["msisdn"])
    op.create_index("ix_telecom_cdrs_call_type", "telecom_cdrs", ["call_type"])
    op.create_index("ix_telecom_cdrs_billed", "telecom_cdrs", ["billed"])


def downgrade() -> None:
    # Drop tables in reverse foreign-key dependency order
    op.drop_index("ix_telecom_cdrs_billed", table_name="telecom_cdrs")
    op.drop_index("ix_telecom_cdrs_call_type", table_name="telecom_cdrs")
    op.drop_index("ix_telecom_cdrs_msisdn", table_name="telecom_cdrs")
    op.drop_table("telecom_cdrs")

    op.drop_index("ix_telecom_subscribers_status", table_name="telecom_subscribers")
    op.drop_index("ix_telecom_subscribers_plan_id", table_name="telecom_subscribers")
    op.drop_index("ix_telecom_subscribers_imsi", table_name="telecom_subscribers")
    op.drop_index("ix_telecom_subscribers_iccid", table_name="telecom_subscribers")
    op.drop_index("ix_telecom_subscribers_msisdn", table_name="telecom_subscribers")
    op.drop_index("ix_telecom_subscribers_owner_user_id", table_name="telecom_subscribers")
    op.drop_table("telecom_subscribers")

    op.drop_index("ix_ecommerce_returns_status", table_name="ecommerce_returns")
    op.drop_index("ix_ecommerce_returns_order_id", table_name="ecommerce_returns")
    op.drop_table("ecommerce_returns")

    op.drop_index("ix_ecommerce_orders_status", table_name="ecommerce_orders")
    op.drop_index("ix_ecommerce_orders_customer_id", table_name="ecommerce_orders")
    op.drop_index("ix_ecommerce_orders_owner_user_id", table_name="ecommerce_orders")
    op.drop_table("ecommerce_orders")

    op.drop_index("ix_ecommerce_products_category", table_name="ecommerce_products")
    op.drop_table("ecommerce_products")

    op.drop_index("ix_fintech_transactions_status", table_name="fintech_transactions")
    op.drop_index("ix_fintech_transactions_destination_account_id", table_name="fintech_transactions")
    op.drop_index("ix_fintech_transactions_source_account_id", table_name="fintech_transactions")
    op.drop_table("fintech_transactions")

    op.drop_index("ix_fintech_accounts_iban", table_name="fintech_accounts")
    op.drop_index("ix_fintech_accounts_owner_user_id", table_name="fintech_accounts")
    op.drop_table("fintech_accounts")

    op.drop_index("ix_healthcare_appointments_status", table_name="healthcare_appointments")
    op.drop_index("ix_healthcare_appointments_start_time", table_name="healthcare_appointments")
    op.drop_index("ix_healthcare_appointments_practitioner_ref", table_name="healthcare_appointments")
    op.drop_index("ix_healthcare_appointments_patient_id", table_name="healthcare_appointments")
    op.drop_table("healthcare_appointments")

    op.drop_index("ix_healthcare_observations_loinc_code", table_name="healthcare_observations")
    op.drop_index("ix_healthcare_observations_patient_id", table_name="healthcare_observations")
    op.drop_table("healthcare_observations")

    op.drop_index("ix_healthcare_patients_owner_user_id", table_name="healthcare_patients")
    op.drop_table("healthcare_patients")
