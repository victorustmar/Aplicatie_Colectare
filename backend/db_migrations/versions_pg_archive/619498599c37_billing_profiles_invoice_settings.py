"""billing profiles + invoice settings

Revision ID: 619498599c37
Revises: 2492f3f4891b
Create Date: 2025-09-30 13:26:57.169264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '619498599c37'
down_revision: Union[str, Sequence[str], None] = '2492f3f4891b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) profil de facturare (1:1 cu companies)
    op.create_table(
        "company_billing_profiles",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("cui", sa.String(length=20), nullable=False),
        sa.Column("reg_com", sa.Text()),
        sa.Column("address_line", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("county", sa.Text()),
        sa.Column("postal_code", sa.Text()),
        sa.Column("country", sa.Text(), nullable=False, server_default=sa.text("'RO'")),
        sa.Column("bank_name", sa.Text()),
        sa.Column("iban", sa.Text()),
        sa.Column("email_billing", postgresql.CITEXT()),
        sa.Column("phone_billing", sa.Text()),
        sa.Column("vat_payer", sa.Boolean()),
        sa.Column("vat_cash", sa.Boolean()),
        sa.Column("e_invoice", sa.Boolean()),
        sa.Column("updated_from_anaf_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'ANAF'")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_cbp_cui", "company_billing_profiles", ["cui"])

    # 2) setări pentru compania BASE (serie/număr etc.)
    op.create_table(
        "company_invoice_settings",
        sa.Column("base_company_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("series_code", sa.Text(), nullable=False, server_default=sa.text("'INV'")),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("year_reset", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("due_days", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("default_vat_rate", sa.Numeric(5, 2), nullable=False, server_default=sa.text("19")),
        sa.ForeignKeyConstraint(["base_company_id"], ["companies.company_id"], ondelete="CASCADE"),
    )

def downgrade() -> None:
    op.drop_table("company_invoice_settings")
    op.drop_index("idx_cbp_cui", table_name="company_billing_profiles")
    op.drop_table("company_billing_profiles")