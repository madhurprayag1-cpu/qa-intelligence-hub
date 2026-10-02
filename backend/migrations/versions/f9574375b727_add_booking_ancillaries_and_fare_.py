"""add booking ancillaries and fare breakdown

Revision ID: f9574375b727
Revises: 76fdc6c41a8a
Create Date: 2026-09-27 17:44:16.376683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9574375b727'
down_revision: Union[str, Sequence[str], None] = '76fdc6c41a8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('base_fare', sa.Numeric(10, 2), server_default='0.00', nullable=False))
    op.add_column('bookings', sa.Column('ancillary_amount', sa.Numeric(10, 2), server_default='0.00', nullable=False))
    op.add_column('bookings', sa.Column('ancillaries', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('bookings', 'ancillaries')
    op.drop_column('bookings', 'ancillary_amount')
    op.drop_column('bookings', 'base_fare')
