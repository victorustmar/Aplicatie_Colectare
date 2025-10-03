"""day2 invitations + collaborations + company_code

Revision ID: 2492f3f4891b
Revises: 98f443b10361
Create Date: 2025-09-26 15:06:41.993640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2492f3f4891b'
down_revision: Union[str, Sequence[str], None] = '98f443b10361'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) companies.company_code (slug unic, 8 hexa)
    op.execute("""
    ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS company_code TEXT
      NOT NULL
      DEFAULT lower(substring(encode(gen_random_bytes(6),'hex') from 1 for 8));
    """)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
         SELECT 1 FROM pg_constraint
         WHERE conname = 'uq_companies_company_code'
      ) THEN
        ALTER TABLE companies
          ADD CONSTRAINT uq_companies_company_code UNIQUE (company_code);
      END IF;
    END$$;
    """)

    # 2) collaborations: relația BASE ↔ CLIENT
    op.execute("""
    CREATE TABLE IF NOT EXISTS collaborations(
      base_company_id   uuid NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
      client_company_id uuid NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
      status            TEXT NOT NULL DEFAULT 'PENDING'
                         CHECK (status IN ('PENDING','ACTIVE','INACTIVE')),
      created_at        timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (base_company_id, client_company_id)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_base   ON collaborations(base_company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_client ON collaborations(client_company_id);")

    # 3) company_invitations: invitații de colaborare
    op.execute("""
    CREATE TABLE IF NOT EXISTS company_invitations(
      invitation_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      base_company_id   uuid NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
      client_company_id uuid     REFERENCES companies(company_id) ON DELETE SET NULL,
      cui               varchar(20) NOT NULL,
      invited_email     citext      NOT NULL,
      token             TEXT        NOT NULL UNIQUE,
      expires_at        timestamptz NOT NULL DEFAULT now() + interval '7 days',
      accepted_at       timestamptz,
      created_at        timestamptz NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_invites_cui   ON company_invitations(cui);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invites_email ON company_invitations(invited_email);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS company_invitations;")
    op.execute("DROP TABLE IF EXISTS collaborations;")
    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS uq_companies_company_code;")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS company_code;")