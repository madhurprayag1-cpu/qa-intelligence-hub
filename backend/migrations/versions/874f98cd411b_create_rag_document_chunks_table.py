"""create rag_document_chunks table

Revision ID: 874f98cd411b
Revises: f9574375b727
Create Date: 2026-09-27 18:07:19.541805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '874f98cd411b'
down_revision: Union[str, Sequence[str], None] = 'f9574375b727'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rag_document_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('chunk_id', sa.String(length=120), nullable=False, unique=True, index=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('rag_document_chunks')

