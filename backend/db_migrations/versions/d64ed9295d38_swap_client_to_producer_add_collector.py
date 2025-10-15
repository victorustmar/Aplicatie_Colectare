"""swap client to producer add collector

Revision ID: d64ed9295d38
Revises: 8b513ab8b109
Create Date: 2025-10-15 19:11:45.744456

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'd64ed9295d38'
down_revision: Union[str, Sequence[str], None] = '8b513ab8b109'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------- helpers ----------
def _insp(bind) -> Inspector:
    return sa.inspect(bind)

def _has_table(bind, table: str) -> bool:
    return _insp(bind).has_table(table)

def _has_column(bind, table: str, col: str) -> bool:
    if not _has_table(bind, table):
        return False
    for c in _insp(bind).get_columns(table):
        if c.get("name") == col:
            return True
    return False

def _is_mysql_enum(bind, table: str, col: str) -> bool:
    q = text(
        """
        SELECT DATA_TYPE
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = :t
           AND COLUMN_NAME = :c
        """
    )
    row = bind.execute(q, {"t": table, "c": col}).mappings().first()
    return bool(row) and (row["DATA_TYPE"] or "").lower() == "enum"


# ---------- upgrade ----------
def upgrade():
    bind = op.get_bind()

    # 1) users.role: extinde ENUM să includă PRODUCER & COLLECTOR (păstrăm CLIENT pentru siguranță)
    if _has_column(bind, "users", "role") and _is_mysql_enum(bind, "users", "role"):
        op.execute(
            """
            ALTER TABLE users
              MODIFY COLUMN role ENUM('ADMIN','BASE','CLIENT','PRODUCER','COLLECTOR','RECYCLER') NOT NULL
            """
        )
        # Convertește datele: CLIENT -> PRODUCER
        op.execute("UPDATE users SET role='PRODUCER' WHERE role='CLIENT'")

    # 2) invites.target_role în INVITES (nou) sau COMPANY_INVITATIONS (vechi)
    #    întâi rescriem valorile ca să putem restrânge enum-ul fără CLIENT
    if _has_column(bind, "invites", "target_role"):
        op.execute("UPDATE invites SET target_role='PRODUCER' WHERE target_role='CLIENT'")
        op.execute(
            """
            ALTER TABLE invites
              MODIFY COLUMN target_role ENUM('PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL DEFAULT 'PRODUCER'
            """
        )
    if _has_column(bind, "company_invitations", "target_role"):
        op.execute("UPDATE company_invitations SET target_role='PRODUCER' WHERE target_role='CLIENT'")
        op.execute(
            """
            ALTER TABLE company_invitations
              MODIFY COLUMN target_role ENUM('PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL DEFAULT 'PRODUCER'
            """
        )

    # 3) relationships.partner_type: adaugă COLLECTOR, mapează CLIENT -> PRODUCER
    if _has_column(bind, "relationships", "partner_type") and _is_mysql_enum(bind, "relationships", "partner_type"):
        # asigurăm toate valorile necesare (păstrăm și CLIENT, ca să nu eșueze în pasul de UPDATE)
        op.execute(
            """
            ALTER TABLE relationships
              MODIFY COLUMN partner_type ENUM('CLIENT','PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL
            """
        )
        op.execute("UPDATE relationships SET partner_type='PRODUCER' WHERE partner_type='CLIENT'")
        # (opțional) dacă vrei să elimini complet CLIENT din enum, decomentează:
        # op.execute(
        #     """
        #     ALTER TABLE relationships
        #       MODIFY COLUMN partner_type ENUM('PRODUCER','COLLECTOR','RECYCLER')
        #       NOT NULL
        #     """
        # )

    # 4) collaborations_view: arată relațiile ca „colaborări” doar pentru PRODUCER
    #    (dacă vrei și compat cu vechiul CLIENT, folosește IN ('PRODUCER','CLIENT'))
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
        WHERE partner_type = 'PRODUCER'
        """
    )


# ---------- downgrade ----------
def downgrade():
    bind = op.get_bind()

    # view: revine la varianta cu CLIENT (ca în migrarea precedentă)
    op.execute("DROP VIEW IF EXISTS collaborations_view")
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

    # relationships.partner_type: mapăm PRODUCER -> CLIENT (doar dacă există enum-ul)
    if _has_column(bind, "relationships", "partner_type") and _is_mysql_enum(bind, "relationships", "partner_type"):
        # asigură enum-ul conține CLIENT (dacă cineva a eliminat între timp)
        op.execute(
            """
            ALTER TABLE relationships
              MODIFY COLUMN partner_type ENUM('CLIENT','PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL
            """
        )
        op.execute("UPDATE relationships SET partner_type='CLIENT' WHERE partner_type='PRODUCER'")

    # invites.target_role: PRODUCER -> CLIENT și re-include CLIENT în enum
    if _has_column(bind, "invites", "target_role"):
        op.execute(
            """
            ALTER TABLE invites
              MODIFY COLUMN target_role ENUM('CLIENT','PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL DEFAULT 'CLIENT'
            """
        )
        op.execute("UPDATE invites SET target_role='CLIENT' WHERE target_role='PRODUCER'")
    if _has_column(bind, "company_invitations", "target_role"):
        op.execute(
            """
            ALTER TABLE company_invitations
              MODIFY COLUMN target_role ENUM('CLIENT','PRODUCER','COLLECTOR','RECYCLER')
              NOT NULL DEFAULT 'CLIENT'
            """
        )
        op.execute("UPDATE company_invitations SET target_role='CLIENT' WHERE target_role='PRODUCER'")

    # users.role: re-include CLIENT ca default logic (păstrăm și noile valori pentru siguranță)
    if _has_column(bind, "users", "role") and _is_mysql_enum(bind, "users", "role"):
        op.execute(
            """
            ALTER TABLE users
              MODIFY COLUMN role ENUM('ADMIN','BASE','CLIENT','PRODUCER','COLLECTOR','RECYCLER') NOT NULL
            """
        )
        op.execute("UPDATE users SET role='CLIENT' WHERE role='PRODUCER'")