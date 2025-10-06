"""add expires_at to company_invitations

Revision ID: 9b039ef656ef
Revises: 2f31cea61b1a
Create Date: 2025-10-05 15:04:51.020077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b039ef656ef'
down_revision: Union[str, Sequence[str], None] = '2f31cea61b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'company_invitations',
        sa.Column('expires_at', sa.DateTime(), nullable=True)
    )
    # optional backfill
    op.execute("""
        UPDATE company_invitations
        SET expires_at = DATE_ADD(created_at, INTERVAL 14 DAY)
        WHERE expires_at IS NULL
    """)

def downgrade():
    op.drop_column('company_invitations', 'expires_at')