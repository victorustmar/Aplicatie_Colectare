"""add roles + relationships + recyclings + packages

Revision ID: bee045b37be5
Revises: 9b039ef656ef
Create Date: 2025-10-15 00:37:55.078539
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "bee045b37be5"
down_revision: Union[str, Sequence[str], None] = "9b039ef656ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Folosim EXACT tipul/colation-ul companiei: VARCHAR(36) / utf8mb4_unicode_ci
CID = sa.String(length=36, collation="utf8mb4_unicode_ci")
TABLE_KW = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")


def _get_inspector(bind) -> Inspector:
    return sa.inspect(bind)


def _table_exists(bind, table_name: str) -> bool:
    insp = _get_inspector(bind)
    return insp.has_table(table_name)


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = _get_inspector(bind)
    if not insp.has_table(table_name):
        return False
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    insp = _get_inspector(bind)
    if not insp.has_table(table_name):
        return False
    idx = [i["name"] for i in insp.get_indexes(table_name)]
    return index_name in idx


def _is_mysql_enum(bind, table_name: str, column_name: str) -> bool:
    q = text(
        """
        SELECT DATA_TYPE
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = :t
           AND COLUMN_NAME = :c
        """
    )
    row = bind.execute(q, {"t": table_name, "c": column_name}).mappings().first()
    if not row:
        return False
    return (row["DATA_TYPE"] or "").lower() == "enum"


def upgrade():
    bind = op.get_bind()

    # 001) users.role + invites.target_role + relationships (+ backfill)
    if _table_exists(bind, "users") and _column_exists(bind, "users", "role") and _is_mysql_enum(bind, "users", "role"):
        op.execute(
            "ALTER TABLE users "
            "MODIFY COLUMN role ENUM('ADMIN','BASE','CLIENT','RECYCLER','PRODUCER') NOT NULL"
        )

    if _table_exists(bind, "invites") and not _column_exists(bind, "invites", "target_role"):
        op.execute(
            "ALTER TABLE invites "
            "ADD COLUMN target_role ENUM('CLIENT','RECYCLER','PRODUCER') NOT NULL DEFAULT 'CLIENT' AFTER token"
        )

    if not _table_exists(bind, "relationships"):
        op.create_table(
            "relationships",
            sa.Column("relationship_id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("base_company_id", CID, nullable=False),
            sa.Column("partner_company_id", CID, nullable=False),
            sa.Column("partner_type", sa.Enum("CLIENT", "RECYCLER", "PRODUCER", name="partner_type_enum"), nullable=False),
            sa.Column(
                "status",
                sa.Enum("PENDING", "ACTIVE", "REJECTED", name="relationship_status_enum"),
                nullable=False,
                server_default="ACTIVE",
            ),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(fsp=6),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            ),
            sa.UniqueConstraint("base_company_id", "partner_company_id", "partner_type", name="uq_relationship"),
            **TABLE_KW,
        )
        # indexuri pe FK-uri (ajută InnoDB să accepte FK-urile)
        op.create_index("idx_rel_base", "relationships", ["base_company_id", "partner_type", "status", "created_at"])
        op.create_index("idx_rel_partner", "relationships", ["partner_company_id", "partner_type", "status", "created_at"])
        # FKs
        op.create_foreign_key("fk_rel_base_company", "relationships", "companies", ["base_company_id"], ["company_id"])
        op.create_foreign_key("fk_rel_partner_company", "relationships", "companies", ["partner_company_id"], ["company_id"])

    if _table_exists(bind, "collaborations"):
        op.execute(
            """
            INSERT IGNORE INTO relationships
                (relationship_id, base_company_id, partner_company_id, partner_type, status, created_at)
            SELECT UUID(), base_company_id, client_company_id, 'CLIENT', status, COALESCE(created_at, NOW(6))
            FROM collaborations
            """
        )

    # 002) recyclings (RECYCLER trimite „reciclări” către BAZĂ)
    if not _table_exists(bind, "recyclings"):
        op.create_table(
            "recyclings",
            sa.Column("recycling_id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("recycler_company_id", CID, nullable=False),
            sa.Column("status", sa.Enum("PENDING", "VALIDATED", name="recycling_status_enum"), nullable=False, server_default="PENDING"),
            sa.Column("batteries", sa.JSON, nullable=False),
            sa.Column("total_weight", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("total_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(fsp=6),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            ),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            **TABLE_KW,
        )
        op.create_index("idx_recyclings_recycler", "recyclings", ["recycler_company_id", "status", "created_at"])
        # index pe col FK înainte de FK (evită erori pe unele versiuni)
        op.create_index("idx_recyclings_recycler_only", "recyclings", ["recycler_company_id"])
        op.create_foreign_key("fk_recycling_recycler", "recyclings", "companies", ["recycler_company_id"], ["company_id"])

    # 003) packages (BAZA trimite „pachete” către PRODUCĂTOR)
    if not _table_exists(bind, "packages"):
        op.create_table(
            "packages",
            sa.Column("package_id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("base_company_id", CID, nullable=False),
            sa.Column("producer_company_id", CID, nullable=False),
            sa.Column("status", sa.Enum("PENDING", "VALIDATED", name="package_status_enum"), nullable=False, server_default="PENDING"),
            sa.Column("batteries", sa.JSON, nullable=False),
            sa.Column("total_weight", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("total_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                mysql.TIMESTAMP(fsp=6),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            ),
            sa.Column("validated_at", sa.DateTime(), nullable=True),
            **TABLE_KW,
        )
        op.create_index("idx_packages_base", "packages", ["base_company_id", "status", "created_at"])
        op.create_index("idx_packages_producer", "packages", ["producer_company_id", "status", "created_at"])
        op.create_index("idx_packages_base_only", "packages", ["base_company_id"])
        op.create_index("idx_packages_producer_only", "packages", ["producer_company_id"])
        op.create_foreign_key("fk_pkg_base", "packages", "companies", ["base_company_id"], ["company_id"])
        op.create_foreign_key("fk_pkg_producer", "packages", "companies", ["producer_company_id"], ["company_id"])

    # 004) invoices: legături opționale către reciclări/pachete
    if _table_exists(bind, "invoices"):
        if not _column_exists(bind, "invoices", "recycling_id"):
            op.add_column("invoices", sa.Column("recycling_id", sa.String(length=36, collation="utf8mb4_unicode_ci"), nullable=True))
        if not _column_exists(bind, "invoices", "package_id"):
            op.add_column("invoices", sa.Column("package_id", sa.String(length=36, collation="utf8mb4_unicode_ci"), nullable=True))

        if not _index_exists(bind, "invoices", "idx_inv_recycling"):
            op.create_index("idx_inv_recycling", "invoices", ["recycling_id"])
        if not _index_exists(bind, "invoices", "idx_inv_package"):
            op.create_index("idx_inv_package", "invoices", ["package_id"])

        if _table_exists(bind, "recyclings"):
            op.create_foreign_key("fk_inv_recycling", "invoices", "recyclings", ["recycling_id"], ["recycling_id"])
        if _table_exists(bind, "packages"):
            op.create_foreign_key("fk_inv_package", "invoices", "packages", ["package_id"], ["package_id"])

    # 005) view compatibilitate
    op.execute(
        """
        CREATE OR REPLACE VIEW collaborations_view AS
        SELECT
          relationship_id AS collaboration_id,
          base_company_id,
          partner_company_id AS client_company_id,
          status,
          created_at
        FROM relationships
        WHERE partner_type = 'CLIENT'
        """
    )


def downgrade():
    bind = op.get_bind()

    op.execute("DROP VIEW IF EXISTS collaborations_view")

    if _table_exists(bind, "invoices"):
        for c in ("fk_inv_package", "fk_inv_recycling"):
            try:
                op.drop_constraint(c, "invoices", type_="foreignkey")
            except Exception:
                pass
        for i in ("idx_inv_package", "idx_inv_recycling"):
            try:
                op.drop_index(i, table_name="invoices")
            except Exception:
                pass
        for col in ("package_id", "recycling_id"):
            if _column_exists(bind, "invoices", col):
                op.drop_column("invoices", col)

    if _table_exists(bind, "packages"):
        for i in ("idx_packages_producer_only", "idx_packages_base_only", "idx_packages_producer", "idx_packages_base"):
            try:
                op.drop_index(i, table_name="packages")
            except Exception:
                pass
        for c in ("fk_pkg_producer", "fk_pkg_base"):
            try:
                op.drop_constraint(c, "packages", type_="foreignkey")
            except Exception:
                pass
        op.drop_table("packages")

    if _table_exists(bind, "recyclings"):
        for i in ("idx_recyclings_recycler_only", "idx_recyclings_recycler"):
            try:
                op.drop_index(i, table_name="recyclings")
            except Exception:
                pass
        try:
            op.drop_constraint("fk_recycling_recycler", "recyclings", type_="foreignkey")
        except Exception:
            pass
        op.drop_table("recyclings")

    if _table_exists(bind, "relationships"):
        for i in ("idx_rel_partner", "idx_rel_base"):
            try:
                op.drop_index(i, table_name="relationships")
            except Exception:
                pass
        for c in ("fk_rel_partner_company", "fk_rel_base_company"):
            try:
                op.drop_constraint(c, "relationships", type_="foreignkey")
            except Exception:
                pass
        op.drop_table("relationships")

    if _table_exists(bind, "invites") and _column_exists(bind, "invites", "target_role"):
        try:
            op.execute("ALTER TABLE invites DROP COLUMN target_role")
        except Exception:
            pass
