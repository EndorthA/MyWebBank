from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import NotFoundError, BadRequestError


router = APIRouter(prefix="/customers", tags=["customers"])


# ============================================================
# Create Customer
# ============================================================
@router.post("/", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer record."""
    try:
        customer = crud.create_customer(db, data)
        return customer
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Get Customer by ID
# ============================================================
@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer details by customer ID."""
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


# ============================================================
# List All Customers
# ============================================================
@router.get("/", response_model=list[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    """List all customers."""
    customers = crud.list_customers(db)
    return customers


# ============================================================
# Update Customer
# ============================================================
@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: int, 
    data: schemas.CustomerCreate, 
    db: Session = Depends(get_db)
):
    """Update customer information."""
    try:
        customer = crud.update_customer(db, customer_id, data)
        return customer
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Soft Delete Customer
# ============================================================
@router.delete("/{customer_id}", response_model=schemas.CustomerOut)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Soft delete a customer (mark as deleted, don't remove from DB)."""
    try:
        customer = crud.soft_delete_customer(db, customer_id)
        return customer
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
