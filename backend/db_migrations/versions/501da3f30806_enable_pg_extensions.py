"""enable pg extensions

Revision ID: 501da3f30806
Revises:
Create Date: 2025-09-25 20:18:00.558883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '501da3f30806'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS citext;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
