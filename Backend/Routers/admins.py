from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import NotFoundError, BadRequestError, AuthError


router = APIRouter(prefix="/admins", tags=["admins"])


# Admin login request model
class AdminLoginRequest(BaseModel):
    username: str
    password: str


# ============================================================
# Create Admin
# ============================================================
@router.post("/", response_model=schemas.AdminOut, status_code=status.HTTP_201_CREATED)
def create_admin(data: schemas.AdminCreate, db: Session = Depends(get_db)):
    """Create a new admin user."""
    try:
        admin = crud.create_admin(db, data)
        return admin
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Get Admin by ID
# ============================================================
@router.get("/{admin_id}", response_model=schemas.AdminOut)
def get_admin(admin_id: int, db: Session = Depends(get_db)):
    """Get admin details by admin ID."""
    admin = crud.get_admin(db, admin_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return admin


# ============================================================
# Get Admin by Username
# ============================================================
@router.get("/username/{username}", response_model=schemas.AdminOut)
def get_admin_by_username(username: str, db: Session = Depends(get_db)):
    """Get admin details by username."""
    admin = crud.get_admin_by_username(db, username)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return admin


# ============================================================
# List All Admins
# ============================================================
@router.get("/", response_model=list[schemas.AdminOut])
def list_admins(db: Session = Depends(get_db)):
    """List all admin users."""
    admins = crud.list_admins(db)
    return admins


# ============================================================
# Update Admin
# ============================================================
@router.put("/{admin_id}", response_model=schemas.AdminOut)
def update_admin(
    admin_id: int, 
    data: schemas.AdminCreate, 
    db: Session = Depends(get_db)
):
    """Update admin information."""
    try:
        admin = crud.update_admin(db, admin_id, data)
        return admin
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================
# Admin Login
# ============================================================
@router.post("/login", response_model=schemas.AdminOut)
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    """Authenticate admin with username and password."""
    try:
        admin = crud.authenticate_admin(db, data.username, data.password)
        return admin
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ============================================================
# Deactivate Admin
# ============================================================
@router.delete("/{admin_id}", response_model=schemas.AdminOut)
def deactivate_admin(admin_id: int, db: Session = Depends(get_db)):
    """Deactivate (soft delete) an admin account."""
    try:
        admin = crud.deactivate_admin(db, admin_id)
        return admin
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
