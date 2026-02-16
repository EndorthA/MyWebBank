"""add role support to users and admins

Revision ID: 2d7f4b5g9e3h
Revises: 1b5cc20e2a36
Create Date: 2026-02-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d7f4b5g9e3h'
down_revision: Union[str, Sequence[str], None] = '1b5cc20e2a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role support to users and admins."""
    # Create user role enum type
    sa.Enum('customer', 'premium_customer', name='userrole').create(op.get_bind(), checkfirst=True)
    
    # Create admin role enum type
    sa.Enum('admin', 'super_admin', 'support_agent', name='adminrole').create(op.get_bind(), checkfirst=True)
    
    # Add role column to users table
    op.add_column('users', sa.Column('role', sa.Enum('customer', 'premium_customer', name='userrole'), 
                                     server_default='customer', nullable=False))
    
    # Add role column to admins table
    op.add_column('admins', sa.Column('role', sa.Enum('admin', 'super_admin', 'support_agent', name='adminrole'),
                                      server_default='admin', nullable=False))


def downgrade() -> None:
    """Remove role support from users and admins."""
    # Drop role column from admins
    op.drop_column('admins', 'role')
    
    # Drop role column from users
    op.drop_column('users', 'role')
    
    # Drop enum types
    sa.Enum('customer', 'premium_customer', name='userrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum('admin', 'super_admin', 'support_agent', name='adminrole').drop(op.get_bind(), checkfirst=True)
