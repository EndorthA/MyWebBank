"""add account name to accounts

Revision ID: c5130d798763
Revises: 2d7f4b5g9e3h
Create Date: 2026-03-04 22:11:03.863085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5130d798763'
down_revision: Union[str, Sequence[str], None] = '2d7f4b5g9e3h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('name', sa.String(length=100), nullable=True))
    op.execute("UPDATE accounts SET name = 'Account ' || account_id WHERE name IS NULL")
    op.alter_column('accounts', 'name', nullable=False)


def downgrade() -> None:
    op.drop_column('accounts', 'name')
