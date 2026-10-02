"""add booking owner user id

Revision ID: c2b674d52e19
Revises: a1d94f7b2c01
Create Date: 2026-09-30 16:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2b674d52e19"
down_revision: Union[str, Sequence[str], None] = "a1d94f7b2c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index("ix_bookings_owner_user_id", "bookings", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_bookings_owner_user_id", table_name="bookings")
    op.drop_column("bookings", "owner_user_id")
