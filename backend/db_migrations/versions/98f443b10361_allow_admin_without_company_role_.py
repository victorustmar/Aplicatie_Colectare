"""allow ADMIN without company + role/company check

Revision ID: 98f443b10361
Revises: 4db3a2a503f8
Create Date: 2025-09-25 22:04:04.699531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98f443b10361'
down_revision: Union[str, Sequence[str], None] = '4db3a2a503f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Permitem NULL pe company_id
    op.alter_column("users", "company_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
                    nullable=True)

    # 2) Constrângere: ADMIN => company_id IS NULL; altfel company_id IS NOT NULL
    # user_role este un ENUM postgres; comparam cu 'ADMIN'::user_role ca să fie sigur
    op.create_check_constraint(
        "ck_users_company_id_for_role",
        "users",
        "( (role = 'ADMIN'::user_role AND company_id IS NULL) "
        "OR (role <> 'ADMIN'::user_role AND company_id IS NOT NULL) )"
    )

def downgrade() -> None:
    # revert: scoatem check-ul si facem iar NOT NULL (atenție: va eșua dacă există ADMIN cu NULL)
    op.drop_constraint("ck_users_company_id_for_role", "users", type_="check")
    op.alter_column("users", "company_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
                    nullable=False)