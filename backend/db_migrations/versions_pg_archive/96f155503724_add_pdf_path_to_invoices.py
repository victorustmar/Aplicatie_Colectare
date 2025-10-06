"""add pdf_path to invoices

Revision ID: 96f155503724
Revises: 71beaca0fb95
Create Date: 2025-10-01 12:03:52.332548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96f155503724'
down_revision: Union[str, Sequence[str], None] = '71beaca0fb95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("invoices", sa.Column("pdf_path", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("invoices", "pdf_path")
