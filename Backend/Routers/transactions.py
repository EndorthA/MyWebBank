from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import NotFoundError, BadRequestError
from .auth import get_current_user


router = APIRouter(prefix="/transactions", tags=["transactions"])


# ============================================================
# Create Transaction
# ============================================================
@router.post("/", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create and execute a new transaction between two accounts."""
    try:
        transaction = crud.create_transaction(db, data)
        return transaction
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Get Transaction by ID
# ============================================================
@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get transaction details by transaction ID."""
    transaction = crud.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


# ============================================================
# List Transactions for Account
# ============================================================
@router.get("/account/{account_id}")
def list_transactions_for_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all transactions (sent and received) for a specific account."""
    transactions = crud.list_transactions_for_account(db, account_id)
    return [schemas.TransactionOut.model_validate(tx) for tx in transactions]