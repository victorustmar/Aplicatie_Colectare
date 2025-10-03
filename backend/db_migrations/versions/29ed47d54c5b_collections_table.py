"""collections table

Revision ID: 29ed47d54c5b
Revises: 619498599c37
Create Date: 2025-09-30 13:54:07.779840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '29ed47d54c5b'
down_revision: Union[str, Sequence[str], None] = '619498599c37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "collections",
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("total_weight", sa.Numeric(12,3)),
        sa.Column("total_cost", sa.Numeric(12,2)),
        sa.Column("batteries", postgresql.JSONB()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("validated_at", sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(["client_company_id"], ["companies.company_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_col_client", "collections", ["client_company_id"])

def downgrade():
    op.drop_index("idx_col_client", table_name="collections")
    op.drop_table("collections")