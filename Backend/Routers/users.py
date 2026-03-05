from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import NotFoundError, BadRequestError, AuthError
from .auth import get_current_admin, get_current_user_or_admin


router = APIRouter(prefix="/users", tags=["users"])


# Login request model
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateUserStatusRequest(BaseModel):
    status_value: str


# ============================================================
# Create User (Register)
# ============================================================
@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user account for an existing customer."""
    try:
        user = crud.create_user(db, data)
        return user
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================
# Get User by ID
# ============================================================
@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details by user ID."""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# ============================================================
# Get Current User
# ============================================================
@router.get("/", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_admin)):
    users = crud.list_users(db)
    return [schemas.UserOut.model_validate(u) for u in users]
# ============================================================
# Get User by Email
# ============================================================
@router.get("/email/{email}", response_model=schemas.UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user details by email address."""
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ============================================================
# Login
# ============================================================
@router.post("/login", response_model=schemas.UserOut)
def login(data: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password."""
    try:
        user = crud.authenticate_user(db, data.email, data.password)
        return user
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ============================================================
# Deactivate User
# ============================================================
@router.delete("/{user_id}", response_model=schemas.UserOut)
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """Deactivate (soft delete) a user account."""
    try:
        user = crud.deactivate_user(db, user_id)
        return user
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================
# Update User Status
# ============================================================
@router.put("/{user_id}/status", response_model=schemas.UserOut)
def update_user_status(
    user_id: int,
    data: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        user = crud.update_user_status(db, user_id, data.status_value)
        return user
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
