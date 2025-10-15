"""add target role to company_invitations

Revision ID: 8b513ab8b109
Revises: bee045b37be5
Create Date: 2025-10-15 06:09:56.868755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '8b513ab8b109'
down_revision: Union[str, Sequence[str], None] = 'bee045b37be5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# db_migrations/versions/2a1b9f1c7d2a_add_target_role_to_company_invitations.py

def upgrade():
    bind = op.get_bind()
    has_col = bind.execute(text("""
        SELECT 1
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'company_invitations'
           AND COLUMN_NAME = 'target_role'
         LIMIT 1
    """)).scalar()
    if not has_col:
        op.execute("""
            ALTER TABLE company_invitations
            ADD COLUMN target_role ENUM('CLIENT','RECYCLER','PRODUCER')
            NOT NULL DEFAULT 'CLIENT'
            AFTER invited_email
        """)

def downgrade():
    bind = op.get_bind()
    has_col = bind.execute(text("""
        SELECT 1
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'company_invitations'
           AND COLUMN_NAME = 'target_role'
         LIMIT 1
    """)).scalar()
    if has_col:
        op.execute("ALTER TABLE company_invitations DROP COLUMN target_role")
