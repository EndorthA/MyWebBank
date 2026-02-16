from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas, models
from ..crud import NotFoundError, BadRequestError
from .auth import get_current_user


router = APIRouter(prefix="/accounts", tags=["accounts"])


# Request models for operations
class DepositRequest(BaseModel):
    amount: Decimal
    currency: str


class WithdrawRequest(BaseModel):
    amount: Decimal
    currency: str


class UpdateStatusRequest(BaseModel):
    status_value: str


# ============================================================
# Create Account
# ============================================================
@router.post("/", response_model=schemas.AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    data: schemas.AccountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new account for a customer."""
    try:
        account = crud.create_account(db, data)
        return account
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Get Account by ID
# ============================================================
@router.get("/{account_id}", response_model=schemas.AccountOut)
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get account details by account ID."""
    account = crud.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


# ============================================================
# List Accounts for Customer
# ============================================================
@router.get("/customer/{customer_id}")
def list_accounts_for_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all accounts for a specific customer."""
    accounts = crud.list_accounts_for_customer(db, customer_id)
    return [schemas.AccountOut.model_validate(acc) for acc in accounts]


# ============================================================
# Update Account Status
# ============================================================
@router.put("/{account_id}/status", response_model=schemas.AccountOut)
def update_account_status(
    account_id: int,
    data: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update account status (active, closed, frozen)."""
    try:
        # Validate status value
        valid_statuses = [s.value for s in models.AccountStatus]
        if data.status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        account = crud.update_account_status(db, account_id, models.AccountStatus(data.status_value))
        return account
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Deposit Money
# ============================================================
@router.post("/{account_id}/deposit", response_model=schemas.AccountOut)
def deposit(
    account_id: int,
    data: DepositRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Deposit money into an account."""
    try:
        account = crud.deposit(db, account_id, data.amount, data.currency)
        return account
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Withdraw Money
# ============================================================
@router.post("/{account_id}/withdraw", response_model=schemas.AccountOut)
def withdraw(
    account_id: int,
    data: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Withdraw money from an account."""
    try:
        account = crud.withdraw(db, account_id, data.amount, data.currency)
        return account
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))