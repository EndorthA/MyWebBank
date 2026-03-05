"""add loan name to loans

Revision ID: 70af58bb7b52
Revises: c5130d798763
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70af58bb7b52'
down_revision: Union[str, Sequence[str], None] = 'c5130d798763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('loans', sa.Column('name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('loans', 'name')
