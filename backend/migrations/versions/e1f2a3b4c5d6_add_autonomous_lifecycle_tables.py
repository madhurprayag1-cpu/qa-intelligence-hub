"""add autonomous lifecycle trace and production intelligence tables

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-10-07 17:30:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requirement_traces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requirement_id", sa.String(length=80), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=40), nullable=False, server_default="cross-domain"),
        sa.Column("impacted_components", sa.JSON(), nullable=False),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=False),
        sa.Column("test_scenarios", sa.JSON(), nullable=False),
        sa.Column("engineering_plan", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="READY_FOR_IMPLEMENTATION"),
        sa.Column("source_sha", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("requirement_id", name="uq_requirement_traces_requirement_id"),
    )
    op.create_index("ix_requirement_traces_requirement_id", "requirement_traces", ["requirement_id"], unique=True)
    op.create_index("ix_requirement_traces_domain", "requirement_traces", ["domain"])
    op.create_index("ix_requirement_traces_status", "requirement_traces", ["status"])
    op.create_index("ix_requirement_traces_source_sha", "requirement_traces", ["source_sha"])

    op.create_table(
        "production_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("observation_id", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("signal", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("serving_sha", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("observation_id", name="uq_production_observations_observation_id"),
    )
    op.create_index("ix_production_observations_observation_id", "production_observations", ["observation_id"], unique=True)
    op.create_index("ix_production_observations_source", "production_observations", ["source"])
    op.create_index("ix_production_observations_signal", "production_observations", ["signal"])
    op.create_index("ix_production_observations_status", "production_observations", ["status"])
    op.create_index("ix_production_observations_serving_sha", "production_observations", ["serving_sha"])

    op.create_table(
        "production_incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("source_sha", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("incident_id", name="uq_production_incidents_incident_id"),
    )
    op.create_index("ix_production_incidents_incident_id", "production_incidents", ["incident_id"], unique=True)
    op.create_index("ix_production_incidents_severity", "production_incidents", ["severity"])
    op.create_index("ix_production_incidents_status", "production_incidents", ["status"])
    op.create_index("ix_production_incidents_source_sha", "production_incidents", ["source_sha"])


def downgrade() -> None:
    op.drop_index("ix_production_incidents_source_sha", table_name="production_incidents")
    op.drop_index("ix_production_incidents_status", table_name="production_incidents")
    op.drop_index("ix_production_incidents_severity", table_name="production_incidents")
    op.drop_index("ix_production_incidents_incident_id", table_name="production_incidents")
    op.drop_table("production_incidents")

    op.drop_index("ix_production_observations_serving_sha", table_name="production_observations")
    op.drop_index("ix_production_observations_status", table_name="production_observations")
    op.drop_index("ix_production_observations_signal", table_name="production_observations")
    op.drop_index("ix_production_observations_source", table_name="production_observations")
    op.drop_index("ix_production_observations_observation_id", table_name="production_observations")
    op.drop_table("production_observations")

    op.drop_index("ix_requirement_traces_source_sha", table_name="requirement_traces")
    op.drop_index("ix_requirement_traces_status", table_name="requirement_traces")
    op.drop_index("ix_requirement_traces_domain", table_name="requirement_traces")
    op.drop_index("ix_requirement_traces_requirement_id", table_name="requirement_traces")
    op.drop_table("requirement_traces")
