"""create quality_gate_runs table

Revision ID: a1d94f7b2c01
Revises: 874f98cd411b
Create Date: 2026-09-27 21:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d94f7b2c01'
down_revision: Union[str, Sequence[str], None] = '874f98cd411b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'quality_gate_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column('policy_name', sa.String(length=64), nullable=False, index=True),
        sa.Column('passed', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(length=32), nullable=False, default="FAILED"),
        sa.Column('pass_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('failure_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_tests', sa.Integer(), nullable=False, default=0),
        sa.Column('passed_tests', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_tests', sa.Integer(), nullable=False, default=0),
        sa.Column('skipped_tests', sa.Integer(), nullable=False, default=0),
        sa.Column('critical_defects', sa.Integer(), nullable=False, default=0),
        sa.Column('contract_failures', sa.Integer(), nullable=False, default=0),
        sa.Column('security_vulnerabilities', sa.Integer(), nullable=False, default=0),
        sa.Column('rag_groundedness_score', sa.Float(), nullable=True),
        sa.Column('violations', sa.JSON(), nullable=True),
        sa.Column('signals', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('quality_gate_runs')
