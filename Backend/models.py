# Backend/models.py
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    Numeric, DateTime, Enum, Text, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# ---------- Enums (stored as TEXT/ENUM in Postgres) ----------
class UserRole(str, enum.Enum):
    """Roles for regular users (customers)."""
    customer = "customer"
    premium_customer = "premium_customer"


class AdminRole(str, enum.Enum):
    """Roles for admin users."""
    admin = "admin"
    super_admin = "super_admin"
    support_agent = "support_agent"


class AccountStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    frozen = "frozen"


class TxStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"


class LoanStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    defaulted = "defaulted"


# ---------- Core entities ----------
class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True)  # Postgres identity handled by migration
    identity_card_num = Column(String(10), nullable=False)
    afm = Column(String(9), nullable=False, unique=True)

    address = Column(String(50))
    zip_code = Column(String(5))
    city = Column(String(20))
    citizenship = Column(String(50))

    is_deleted = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="customer", uselist=False)
    accounts = relationship("Account", back_populates="customer")
    loans = relationship("Loan", back_populates="customer")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False, unique=True)

    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20), unique=True)

    password_hash = Column(String(255), nullable=False)  # DO NOT store plaintext
    failed_login_count = Column(Integer, nullable=False, server_default="0")
    role = Column(Enum(UserRole), nullable=False, server_default=UserRole.customer.value)
    is_deleted = Column(Boolean, nullable=False, server_default="false")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer = relationship("Customer", back_populates="user")


class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)

    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True)

    password_hash = Column(String(255), nullable=False)
    failed_login_count = Column(Integer, nullable=False, server_default="0")
    role = Column(Enum(AdminRole), nullable=False, server_default=AdminRole.admin.value)
    is_deleted = Column(Boolean, nullable=False, server_default="false")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------- Banking ----------
class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False)

    # If you want to keep card number, store only last4 or tokenized value.
    card_nr = Column(String(16), unique=True)  # optional
    currency = Column(String(3), nullable=False)  # "EUR"
    balance = Column(Numeric(14, 2), nullable=False, server_default="0")  # cached balance (optional)

    status = Column(Enum(AccountStatus), nullable=False, server_default=AccountStatus.active.value)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer = relationship("Customer", back_populates="accounts")

    sent_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.sender_account_id",
        back_populates="sender_account",
    )
    received_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.receiver_account_id",
        back_populates="receiver_account",
    )

    __table_args__ = (
        CheckConstraint("char_length(currency) = 3", name="ck_accounts_currency_len"),
        CheckConstraint("balance >= 0", name="ck_accounts_balance_nonneg"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)

    sender_account_id = Column(Integer, ForeignKey("accounts.account_id", ondelete="RESTRICT"), nullable=False)
    receiver_account_id = Column(Integer, ForeignKey("accounts.account_id", ondelete="RESTRICT"), nullable=False)

    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    comment = Column(String(200))

    is_recurring = Column(Boolean, nullable=False, server_default="false")
    status = Column(Enum(TxStatus), nullable=False, server_default=TxStatus.pending.value)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

    sender_account = relationship("Account", foreign_keys=[sender_account_id], back_populates="sent_transactions")
    receiver_account = relationship("Account", foreign_keys=[receiver_account_id], back_populates="received_transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_tx_amount_pos"),
        CheckConstraint("char_length(currency) = 3", name="ck_tx_currency_len"),
        CheckConstraint("sender_account_id <> receiver_account_id", name="ck_tx_not_same_account"),
    )


class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="RESTRICT"), nullable=False)

    principal = Column(Numeric(14, 2), nullable=False)
    remaining_debt = Column(Numeric(14, 2), nullable=False)

    currency = Column(String(3), nullable=False)
    rate_percentage = Column(Numeric(5, 2), nullable=False)

    status = Column(Enum(LoanStatus), nullable=False, server_default=LoanStatus.active.value)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    customer = relationship("Customer", back_populates="loans")

    __table_args__ = (
        CheckConstraint("principal > 0", name="ck_loan_principal_pos"),
        CheckConstraint("remaining_debt >= 0", name="ck_loan_remaining_nonneg"),
        CheckConstraint("char_length(currency) = 3", name="ck_loan_currency_len"),
    )