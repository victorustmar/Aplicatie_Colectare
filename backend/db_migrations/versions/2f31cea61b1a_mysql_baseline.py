"""mysql baseline

Revision ID: 2f31cea61b1a
Revises: 
Create Date: 2025-10-04 19:58:25.896354

"""
from typing import Sequence, Union
from sqlalchemy.dialects import mysql

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f31cea61b1a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Helpers for MySQL defaults
NOW6 = sa.text("CURRENT_TIMESTAMP(6)")
UUID_FN = sa.text("uuid()")  # MySQL returns 36-char string
UTF8 = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

def upgrade() -> None:
    # --- companies ---
    op.create_table(
        "companies",
        sa.Column("company_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("company_type", sa.String(16), nullable=False),  # 'BASE' | 'CLIENT' | 'ADMIN' holder
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cui", sa.String(20), nullable=True, unique=True),
        sa.Column("email_contact", sa.String(254), nullable=True),
        sa.Column("company_code", sa.String(32), nullable=True, unique=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True),
        sa.Column("role", sa.String(16), nullable=False),  # 'ADMIN' | 'BASE' | 'CLIENT'
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )

    # --- user_sessions ---
    op.create_table(
        "user_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),  # INET -> string
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        sa.Column("revoked_at", mysql.DATETIME(fsp=6), nullable=True),
        **UTF8
    )
    op.create_index("idx_user_sessions_user_jti", "user_sessions", ["user_id", "jti"])

    # --- anaf_queries (cache/log) ---
    op.create_table(
        "anaf_queries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cui", sa.String(20), nullable=False, index=True),
        sa.Column("query_date", sa.String(10), nullable=False),  # yyyy-mm-dd
        sa.Column("raw_response", sa.JSON(), nullable=True),     # JSONB -> JSON
        sa.Column("result_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.String(45), nullable=True),    # INET -> string
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )
    op.create_index("idx_anaf_queries_cui_created", "anaf_queries", ["cui", "created_at"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),          # JSONB -> JSON
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )
    op.create_index("idx_audit_actor_created", "audit_logs", ["actor_user_id", "created_at"])

    # --- company_invitations ---
    op.create_table(
        "company_invitations",
        sa.Column("invitation_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("base_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cui", sa.String(20), nullable=False),
        sa.Column("invited_email", sa.String(254), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        sa.Column("accepted_at", mysql.DATETIME(fsp=6), nullable=True),
        **UTF8
    )

    # --- collaborations ---
    op.create_table(
        "collaborations",
        sa.Column("base_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("client_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'")),  # 'PENDING' | 'ACTIVE'
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )

    # --- company_billing_profiles (1:1 with companies) ---
    op.create_table(
        "company_billing_profiles",
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("cui", sa.String(20), nullable=False),
        sa.Column("reg_com", sa.Text(), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("county", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("country", sa.String(2), nullable=False, server_default=sa.text("'RO'")),
        sa.Column("bank_name", sa.Text(), nullable=True),
        sa.Column("iban", sa.Text(), nullable=True),
        sa.Column("email_billing", sa.String(254), nullable=True),  # CITEXT -> normal string (MySQL is case-insensitive by default)
        sa.Column("phone_billing", sa.Text(), nullable=True),
        sa.Column("vat_payer", sa.Boolean(), nullable=True),
        sa.Column("vat_cash", sa.Boolean(), nullable=True),
        sa.Column("e_invoice", sa.Boolean(), nullable=True),
        sa.Column("updated_from_anaf_at", mysql.DATETIME(fsp=6), nullable=True),  # store UTC datetimes from app
        sa.Column("source", sa.String(16), nullable=False, server_default=sa.text("'ANAF'")),
        **UTF8
    )
    op.create_index("idx_cbp_cui", "company_billing_profiles", ["cui"])

    # --- company_invoice_settings (1:1 with base company) ---
    op.create_table(
        "company_invoice_settings",
        sa.Column("base_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("series_code", sa.String(16), nullable=False, server_default=sa.text("'INV'")),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("year_reset", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("due_days", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("default_vat_rate", sa.Numeric(5, 2), nullable=False, server_default=sa.text("19.00")),
        **UTF8
    )

    # --- collections ---
    op.create_table(
        "collections",
        sa.Column("collection_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("client_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("batteries", sa.JSON(), nullable=True),  # JSONB -> JSON
        sa.Column("total_weight", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        sa.Column("validated_at", mysql.DATETIME(fsp=6), nullable=True),
        **UTF8
    )
    op.create_index("idx_collections_client_created", "collections", ["client_company_id", "created_at"])

    # --- invoices ---
    op.create_table(
        "invoices",
        sa.Column("invoice_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("base_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_company_id", sa.String(36), sa.ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("collections.collection_id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_number", sa.String(64), nullable=False, unique=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default=sa.text("'RON'")),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ISSUED'")),
        sa.Column("pdf_path", sa.String(512), nullable=True),  # merged in baseline
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False, server_default=NOW6),
        **UTF8
    )
    op.create_index("idx_invoices_base_created", "invoices", ["base_company_id", "created_at"])
    op.create_index("idx_invoices_client_created", "invoices", ["client_company_id", "created_at"])

    # --- invoice_items ---
    op.create_table(
        "invoice_items",
        sa.Column("item_id", sa.String(36), primary_key=True, server_default=UUID_FN),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        **UTF8
    )
    op.create_index("idx_invoice_items_inv_line", "invoice_items", ["invoice_id", "line_no"])

def downgrade() -> None:
    op.drop_table("invoice_items")
    op.drop_index("idx_invoices_client_created", table_name="invoices")
    op.drop_index("idx_invoices_base_created", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("idx_collections_client_created", table_name="collections")
    op.drop_table("collections")
    op.drop_table("company_invoice_settings")
    op.drop_index("idx_cbp_cui", table_name="company_billing_profiles")
    op.drop_table("company_billing_profiles")
    op.drop_table("collaborations")
    op.drop_table("company_invitations")
    op.drop_index("idx_audit_actor_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_anaf_queries_cui_created", table_name="anaf_queries")
    op.drop_table("anaf_queries")
    op.drop_index("idx_user_sessions_user_jti", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("companies")