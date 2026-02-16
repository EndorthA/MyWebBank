from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import NotFoundError, BadRequestError
from .auth import get_current_user


router = APIRouter(prefix="/loans", tags=["loans"])


# Request model for loan payment
class LoanPaymentRequest(BaseModel):
    amount: Decimal


# ============================================================
# Create Loan
# ============================================================
@router.post("/", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    data: schemas.LoanCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new loan for a customer."""
    try:
        loan = crud.create_loan(db, data)
        return loan
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Get Loan by ID
# ============================================================
@router.get("/{loan_id}", response_model=schemas.LoanOut)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get loan details by loan ID."""
    loan = crud.get_loan(db, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


# ============================================================
# List Loans for Customer
# ============================================================
@router.get("/customer/{customer_id}")
def list_loans_for_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all loans for a specific customer."""
    loans = crud.list_loans_for_customer(db, customer_id)
    return [schemas.LoanOut.model_validate(loan) for loan in loans]


# ============================================================
# Make Loan Payment
# ============================================================
@router.post("/{loan_id}/payment", response_model=schemas.LoanOut)
def make_loan_payment(
    loan_id: int,
    data: LoanPaymentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Make a payment towards a loan."""
    try:
        loan = crud.make_loan_payment(db, loan_id, data.amount)
        return loan
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
