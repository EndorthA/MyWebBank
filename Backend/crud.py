# Backend/crud.py
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from . import models, schemas
from .security import hash_password, verify_password


# ============================================================
# Custom Exceptions
# ============================================================

class NotFoundError(Exception):
    pass


class BadRequestError(Exception):
    pass


class AuthError(Exception):
    pass


# ============================================================
# Customers
# ============================================================

def create_customer(db: Session, data: schemas.CustomerCreate):
    customer = models.Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int):
    return db.get(models.Customer, customer_id)


def list_customers(db: Session):
    return list(db.execute(select(models.Customer)).scalars().all())


def update_customer(db: Session, customer_id: int, data: schemas.CustomerCreate):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise NotFoundError("Customer not found")

    for key, value in data.model_dump().items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


def soft_delete_customer(db: Session, customer_id: int):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise NotFoundError("Customer not found")

    customer.is_deleted = True
    db.commit()
    db.refresh(customer)
    return customer


# ============================================================
# Users
# ============================================================

def create_user(db: Session, data: schemas.UserCreate):
    user = models.User(
        customer_id=data.customer_id,
        email=str(data.email) if data.email else None,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role or models.UserRole.customer.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int):
    return db.get(models.User, user_id)


def get_user_by_email(db: Session, email: str):
    return db.execute(
        select(models.User).where(models.User.email == email)
    ).scalars().first()


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or user.is_deleted:
        raise AuthError("Invalid credentials")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        db.commit()
        raise AuthError("Invalid credentials")

    user.failed_login_count = 0
    db.commit()
    return user


def deactivate_user(db: Session, user_id: int):
    user = db.get(models.User, user_id)
    if not user:
        raise NotFoundError("User not found")

    user.is_deleted = True
    db.commit()
    db.refresh(user)
    return user


# ============================================================
# Admins
# ============================================================

def create_admin(db: Session, data: schemas.AdminCreate):
    admin = models.Admin(
        username=data.username,
        email=str(data.email),
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role or models.AdminRole.admin.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_admin(db: Session, admin_id: int):
    return db.get(models.Admin, admin_id)


def get_admin_by_username(db: Session, username: str):
    return db.execute(
        select(models.Admin).where(models.Admin.username == username)
    ).scalars().first()


def list_admins(db: Session):
    return list(db.execute(select(models.Admin)).scalars().all())


def update_admin(db: Session, admin_id: int, data: schemas.AdminCreate):
    admin = db.get(models.Admin, admin_id)
    if not admin:
        raise NotFoundError("Admin not found")

    admin.username = data.username
    admin.email = str(data.email)
    admin.phone = data.phone
    admin.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(admin)
    return admin


def deactivate_admin(db: Session, admin_id: int):
    admin = db.get(models.Admin, admin_id)
    if not admin:
        raise NotFoundError("Admin not found")

    admin.is_deleted = True
    db.commit()
    db.refresh(admin)
    return admin


def authenticate_admin(db: Session, username: str, password: str):
    admin = get_admin_by_username(db, username)
    if not admin or admin.is_deleted:
        raise AuthError("Invalid credentials")

    if not verify_password(password, admin.password_hash):
        admin.failed_login_count += 1
        db.commit()
        raise AuthError("Invalid credentials")

    admin.failed_login_count = 0
    db.commit()
    return admin


# ============================================================
# Accounts
# ============================================================

def create_account(db: Session, data: schemas.AccountCreate):
    account = models.Account(
        customer_id=data.customer_id,
        name=data.name,
        currency=data.currency.upper(),
        card_nr=data.card_nr,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account(db: Session, account_id: int):
    return db.get(models.Account, account_id)


def list_users(db: Session):
    return list(db.execute(select(models.User)).scalars().all())


def list_accounts_for_customer(db: Session, customer_id: int):
    return list(
        db.execute(
            select(models.Account).where(models.Account.customer_id == customer_id)
        ).scalars().all()
    )


def update_account_status(db: Session, account_id: int, status: models.AccountStatus):
    account = db.get(models.Account, account_id)
    if not account:
        raise NotFoundError("Account not found")

    account.status = status
    db.commit()
    db.refresh(account)
    return account


def deposit(db: Session, account_id: int, amount: Decimal, currency: str):
    if amount <= 0:
        raise BadRequestError("Amount must be positive")

    account = db.execute(
        select(models.Account)
        .where(models.Account.account_id == account_id)
        .with_for_update()
    ).scalars().first()

    if not account:
        raise NotFoundError("Account not found")

    if account.currency != currency.upper():
        raise BadRequestError("Currency mismatch")

    account.balance += amount
    db.commit()
    db.refresh(account)
    return account


def withdraw(db: Session, account_id: int, amount: Decimal, currency: str):
    if amount <= 0:
        raise BadRequestError("Amount must be positive")

    account = db.execute(
        select(models.Account)
        .where(models.Account.account_id == account_id)
        .with_for_update()
    ).scalars().first()

    if not account:
        raise NotFoundError("Account not found")

    if account.currency != currency.upper():
        raise BadRequestError("Currency mismatch")

    if account.balance < amount:
        raise BadRequestError("Insufficient funds")

    account.balance -= amount
    db.commit()
    db.refresh(account)
    return account


# ============================================================
# Transactions
# ============================================================

def create_transaction(db: Session, data: schemas.TransactionCreate):
    if data.sender_account_id == data.receiver_account_id:
        raise BadRequestError("Sender and receiver must differ")

    sender = db.execute(
        select(models.Account)
        .where(models.Account.account_id == data.sender_account_id)
        .with_for_update()
    ).scalars().first()

    receiver = db.execute(
        select(models.Account)
        .where(models.Account.account_id == data.receiver_account_id)
        .with_for_update()
    ).scalars().first()

    if not sender or not receiver:
        raise NotFoundError("Account not found")

    if sender.currency != data.currency.upper():
        raise BadRequestError("Currency mismatch")

    if sender.balance < data.amount:
        raise BadRequestError("Insufficient funds")

    tx = models.Transaction(
        sender_account_id=sender.account_id,
        receiver_account_id=receiver.account_id,
        amount=data.amount,
        currency=data.currency.upper(),
        comment=data.comment,
        is_recurring=data.is_recurring,
        status=models.TxStatus.completed,
    )

    sender.balance -= data.amount
    receiver.balance += data.amount

    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_transaction(db: Session, transaction_id: int):
    return db.get(models.Transaction, transaction_id)


def list_transactions_for_account(db: Session, account_id: int):
    return list(
        db.execute(
            select(models.Transaction).where(
                or_(
                    models.Transaction.sender_account_id == account_id,
                    models.Transaction.receiver_account_id == account_id,
                )
            )
        ).scalars().all()
    )


# ============================================================
# Loans
# ============================================================

def create_loan(db: Session, data: schemas.LoanCreate):
    loan = models.Loan(
        customer_id=data.customer_id,
        name=data.name,
        principal=data.principal,
        remaining_debt=data.remaining_debt,
        currency=data.currency.upper(),
        rate_percentage=data.rate_percentage,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def get_loan(db: Session, loan_id: int):
    return db.get(models.Loan, loan_id)


def list_loans_for_customer(db: Session, customer_id: int):
    return list(
        db.execute(
            select(models.Loan).where(models.Loan.customer_id == customer_id)
        ).scalars().all()
    )


def make_loan_payment(db: Session, loan_id: int, amount: Decimal):
    loan = db.execute(
        select(models.Loan)
        .where(models.Loan.loan_id == loan_id)
        .with_for_update()
    ).scalars().first()

    if not loan:
        raise NotFoundError("Loan not found")

    if amount <= 0:
        raise BadRequestError("Amount must be positive")

    loan.remaining_debt -= amount

    if loan.remaining_debt <= 0:
        loan.remaining_debt = Decimal("0.00")
        loan.status = models.LoanStatus.closed

    db.commit()
    db.refresh(loan)
    return loan


# ============================================================
# Authentication with Tokens (using JWT)
# ============================================================

def login_user(db: Session, email: str, password: str) -> dict:
    """
    Authenticate a user and return tokens.
    
    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": UserOut
        }
    """
    user = authenticate_user(db, email, password)
    
    from .security import create_access_token, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES
    
    access_token = create_access_token(
        user_id=user.user_id,
        user_type="user",
        role=user.role,
        email_or_username=user.email or "",
    )
    
    refresh_token = create_refresh_token(
        user_id=user.user_id,
        user_type="user",
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


def login_admin(db: Session, username: str, password: str) -> dict:
    """
    Authenticate an admin and return tokens.
    
    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "bearer",
            "expires_in": 3600,
            "admin": AdminOut
        }
    """
    admin = authenticate_admin(db, username, password)
    
    from .security import create_access_token, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES
    
    access_token = create_access_token(
        user_id=admin.admin_id,
        user_type="admin",
        role=admin.role,
        email_or_username=admin.username,
    )
    
    refresh_token = create_refresh_token(
        user_id=admin.admin_id,
        user_type="admin",
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "admin": admin,
    }
