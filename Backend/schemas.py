# Backend/schemas.py
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ----------------------------
# Customer
# ----------------------------
class CustomerCreate(BaseModel):
    identity_card_num: str = Field(min_length=1, max_length=10)
    afm: str = Field(min_length=9, max_length=9)

    address: Optional[str] = Field(default=None, max_length=50)
    zip_code: Optional[str] = Field(default=None, max_length=5)
    city: Optional[str] = Field(default=None, max_length=20)
    citizenship: Optional[str] = Field(default=None, max_length=50)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    customer_id: int
    identity_card_num: str
    afm: str

    address: Optional[str]
    zip_code: Optional[str]
    city: Optional[str]
    citizenship: Optional[str]

    is_deleted: bool
    created_at: datetime


# ----------------------------
# User
# ----------------------------
class UserCreate(BaseModel):
    customer_id: int
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[str] = Field(default="customer", description="User role (customer or premium_customer)")
    # Plain password comes from client; you will hash it in security.py / crud.py
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    customer_id: int
    email: Optional[EmailStr]
    phone: Optional[str]
    role: str
    failed_login_count: int
    is_deleted: bool
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


# ----------------------------
# Admin
# ----------------------------
class AdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[str] = Field(default="admin", description="Admin role (admin, super_admin, or support_agent)")
    password: str = Field(min_length=8, max_length=128)


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    admin_id: int
    username: str
    email: EmailStr
    phone: Optional[str]
    role: str
    failed_login_count: int
    is_deleted: bool
    created_at: datetime


class AdminLogin(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


# ----------------------------
# Auth Response
# ----------------------------
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


# ----------------------------
# Account
# ----------------------------
class AccountCreate(BaseModel):
    customer_id: int
    currency: str = Field(min_length=3, max_length=3)  # "EUR"
    card_nr: Optional[str] = Field(default=None, min_length=16, max_length=16)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    account_id: int
    customer_id: int
    card_nr: Optional[str]
    currency: str
    balance: Decimal
    status: str
    created_at: datetime


# ----------------------------
# Transaction
# ----------------------------
class TransactionCreate(BaseModel):
    sender_account_id: int
    receiver_account_id: int
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    comment: Optional[str] = Field(default=None, max_length=200)
    is_recurring: bool = False


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    transaction_id: int
    sender_account_id: int
    receiver_account_id: int
    amount: Decimal
    currency: str
    comment: Optional[str]
    is_recurring: bool
    status: str
    created_at: datetime
    executed_at: Optional[datetime]


# ----------------------------
# Loan
# ----------------------------
class LoanCreate(BaseModel):
    customer_id: int
    principal: Decimal = Field(gt=0)
    remaining_debt: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    rate_percentage: Decimal = Field(gt=0)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    loan_id: int
    customer_id: int
    principal: Decimal
    remaining_debt: Decimal
    currency: str
    rate_percentage: Decimal
    status: str
    created_at: datetime