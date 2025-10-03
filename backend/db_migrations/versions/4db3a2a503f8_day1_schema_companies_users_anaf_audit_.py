"""day1 schema: companies, users, anaf, audit, sessions

Revision ID: 4db3a2a503f8
Revises: 0001_enable_pg_extensions
Create Date: 2025-09-25 21:10:52.627934

"""
from typing import Sequence, Union

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4db3a2a503f8'
down_revision: Union[str, Sequence[str], None] = '501da3f30806'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) create enums once, idempotent
    op.execute("""
    DO $$
    BEGIN
      CREATE TYPE user_role AS ENUM ('ADMIN','BASE','CLIENT');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
      CREATE TYPE company_type AS ENUM ('BASE','CLIENT');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)

    # 2) enum objects used on columns, but DO NOT auto-create them again
    user_role_t = PGEnum('ADMIN', 'BASE', 'CLIENT', name='user_role', create_type=False)
    company_type_t = PGEnum('BASE', 'CLIENT', name='company_type', create_type=False)

    # 3) Funcție updated_at
    op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER LANGUAGE plpgsql AS $$
    BEGIN
      NEW.updated_at := now();
      RETURN NEW;
    END$$;
    """)

    # 4) Tabela companies
    op.create_table(
        "companies",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_type", company_type_t, nullable=False),  # <-- folosește company_type_t
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("cui", sa.String(length=20), nullable=False, unique=True),
        sa.Column("reg_com", sa.Text()),
        sa.Column("email_contact", postgresql.CITEXT()),
        sa.Column("phone_contact", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_companies_cui", "companies", ["cui"])
    op.create_index("idx_companies_type", "companies", ["company_type"])
    op.execute("""
    CREATE TRIGGER companies_set_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # 5) Tabela users
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role_t, nullable=False),             # <-- folosește user_role_t
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="CASCADE"),
    )

    # 6) Tabela anaf_queries
    op.create_table(
        "anaf_queries",
        sa.Column("anaf_query_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("cui", sa.String(length=20), nullable=False),
        sa.Column("query_date", sa.Date(), nullable=False),
        sa.Column("result_code", sa.Integer()),
        sa.Column("message", sa.Text()),
        sa.Column("raw_response", postgresql.JSONB(), nullable=False),
        sa.Column("client_ip", postgresql.INET()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_anaf_cui", "anaf_queries", ["cui"])
    op.create_index("idx_anaf_date", "anaf_queries", ["query_date"])

    # 7) Tabela audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_company_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_table", sa.Text()),
        sa.Column("target_id", sa.Text()),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("details", postgresql.JSONB()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["actor_company_id"], ["companies.company_id"]),
    )
    op.create_index("idx_audit_user_time", "audit_logs", ["actor_user_id", "occurred_at"])

    # 8) Tabela user_sessions
    op.create_table(
        "user_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("jti", sa.Text(), unique=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_sessions_user", "user_sessions", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_sessions_user", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("idx_audit_user_time", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_anaf_date", table_name="anaf_queries")
    op.drop_index("idx_anaf_cui", table_name="anaf_queries")
    op.drop_table("anaf_queries")

    op.drop_table("users")

    op.execute("DROP TRIGGER IF EXISTS companies_set_updated_at ON companies;")
    op.drop_index("idx_companies_type", table_name="companies")
    op.drop_index("idx_companies_cui", table_name="companies")
    op.drop_table("companies")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    # la final – doar dacă nu mai există tabele care le folosesc
    op.execute("DROP TYPE IF EXISTS user_role;")
    op.execute("DROP TYPE IF EXISTS company_type;")