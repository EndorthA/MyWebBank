"""banking schema

Revision ID: 1b5cc20e2a36
Revises: b362bf21f387
Create Date: 2026-02-14 21:23:23.952026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b5cc20e2a36'
down_revision: Union[str, Sequence[str], None] = 'b362bf21f387'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'admins',
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('admin_id'),
        sa.UniqueConstraint('phone'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_admins_email'), 'admins', ['email'], unique=True)

    op.create_table(
        'customers',
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('identity_card_num', sa.String(length=10), nullable=False),
        sa.Column('afm', sa.String(length=9), nullable=False),
        sa.Column('address', sa.String(length=50), nullable=True),
        sa.Column('zip_code', sa.String(length=5), nullable=True),
        sa.Column('city', sa.String(length=20), nullable=True),
        sa.Column('citizenship', sa.String(length=50), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('customer_id'),
        sa.UniqueConstraint('afm'),
    )

    op.create_table(
        'accounts',
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('card_nr', sa.String(length=16), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('balance', sa.Numeric(precision=14, scale=2), server_default='0', nullable=False),
        sa.Column('status', sa.Enum('active', 'closed', 'frozen', name='accountstatus'), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('balance >= 0', name='ck_accounts_balance_nonneg'),
        sa.CheckConstraint('char_length(currency) = 3', name='ck_accounts_currency_len'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('account_id'),
        sa.UniqueConstraint('card_nr'),
    )

    op.create_table(
        'loans',
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('principal', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('remaining_debt', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('rate_percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('status', sa.Enum('active', 'closed', 'defaulted', name='loanstatus'), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('char_length(currency) = 3', name='ck_loan_currency_len'),
        sa.CheckConstraint('principal > 0', name='ck_loan_principal_pos'),
        sa.CheckConstraint('remaining_debt >= 0', name='ck_loan_remaining_nonneg'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('loan_id'),
    )

    op.create_table(
        'transactions',
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('sender_account_id', sa.Integer(), nullable=False),
        sa.Column('receiver_account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('comment', sa.String(length=200), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'completed', 'failed', name='txstatus'), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('amount > 0', name='ck_tx_amount_pos'),
        sa.CheckConstraint('char_length(currency) = 3', name='ck_tx_currency_len'),
        sa.CheckConstraint('sender_account_id <> receiver_account_id', name='ck_tx_not_same_account'),
        sa.ForeignKeyConstraint(['receiver_account_id'], ['accounts.account_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sender_account_id'], ['accounts.account_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('transaction_id'),
    )

    op.alter_column(
        'users',
        'id',
        existing_type=sa.Integer(),
        new_column_name='user_id',
        existing_nullable=False,
    )
    op.add_column('users', sa.Column('customer_id', sa.Integer(), nullable=False))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=False))
    op.add_column('users', sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.alter_column(
        'users',
        'email',
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.create_unique_constraint(None, 'users', ['phone'])
    op.create_foreign_key(None, 'users', 'customers', ['customer_id'], ['customer_id'], ondelete='RESTRICT')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_constraint(None, 'users', type_='unique')
    op.alter_column(
        'users',
        'email',
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'is_deleted')
    op.drop_column('users', 'failed_login_count')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'customer_id')
    op.alter_column(
        'users',
        'user_id',
        existing_type=sa.Integer(),
        new_column_name='id',
        existing_nullable=False,
    )

    op.drop_table('transactions')
    op.drop_table('loans')
    op.drop_table('accounts')
    op.drop_table('customers')
    op.drop_index(op.f('ix_admins_email'), table_name='admins')
    op.drop_table('admins')
