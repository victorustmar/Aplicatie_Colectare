"""invoices schema

Revision ID: 71beaca0fb95
Revises: 29ed47d54c5b
Create Date: 2025-09-30 14:26:08.998216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '71beaca0fb95'
down_revision: Union[str, Sequence[str], None] = '29ed47d54c5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) invoices (cap de factură)
    op.create_table(
        "invoices",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("base_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False, server_default=sa.text("current_date")),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'RON'")),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default=sa.text("19")),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ISSUED'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["base_company_id"], ["companies.company_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_company_id"], ["companies.company_id"], ondelete="CASCADE"),
        # dacă ai un FK către collections:
        sa.ForeignKeyConstraint(["collection_id"], ["collections.collection_id"], ondelete="SET NULL"),
        sa.CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonneg"),
        sa.CheckConstraint("vat_amount >= 0", name="ck_invoices_vat_nonneg"),
        sa.CheckConstraint("total >= 0", name="ck_invoices_total_nonneg"),
        sa.CheckConstraint("vat_rate >= 0 AND vat_rate < 100", name="ck_invoices_vat_rate_range"),
    )
    # Unicitate număr pe compania BASE
    op.create_index(
        "uq_invoice_per_base",
        "invoices",
        ["base_company_id", "invoice_number"],
        unique=True,
    )
    # O factură per colectare (dacă ai collection_id setat) – index unic parțial
    op.create_index(
        "uq_invoice_per_collection",
        "invoices",
        ["collection_id"],
        unique=True,
        postgresql_where=sa.text("collection_id IS NOT NULL"),
    )

    # 2) invoice_items
    op.create_table(
        "invoice_items",
        sa.Column("item_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False, server_default=sa.text("1")),
        sa.Column("unit", sa.Text(), nullable=False, server_default=sa.text("'buc'")),  # sau 'kg'
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.invoice_id"], ondelete="CASCADE"),
        sa.CheckConstraint("qty >= 0", name="ck_items_qty_nonneg"),
        sa.CheckConstraint("unit_price >= 0", name="ck_items_price_nonneg"),
        sa.CheckConstraint("line_total >= 0", name="ck_items_total_nonneg"),
    )
    op.create_index("idx_items_invoice", "invoice_items", ["invoice_id"])

    # 3) invoice_pdfs (stocare PDF în DB sau pe disc)
    op.create_table(
        "invoice_pdfs",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),  # alternativ, păstrezi path pe disc
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.invoice_id"], ondelete="CASCADE"),
        sa.CheckConstraint("(pdf_bytes IS NOT NULL) OR (pdf_path IS NOT NULL)", name="ck_pdf_has_data"),
    )

def downgrade() -> None:
    op.drop_table("invoice_pdfs")
    op.drop_index("idx_items_invoice", table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index("uq_invoice_per_collection", table_name="invoices")
    op.drop_index("uq_invoice_per_base", table_name="invoices")
    op.drop_table("invoices")