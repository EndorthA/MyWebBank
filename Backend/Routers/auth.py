# Backend/Routers/auth.py
"""
Authentication endpoints for users and admins.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas
from ..crud import AuthError, NotFoundError


router = APIRouter(tags=["auth"])


# ============================================================
# User Login
# ============================================================
@router.post("/auth/login", response_model=schemas.TokenResponse)
def user_login(
    credentials: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    """
    Login a customer user and return JWT tokens.
    
    **Request:**
    ```json
    {
        "email": "user@example.com",
        "password": "password123"
    }
    ```
    
    **Response:**
    ```json
    {
        "access_token": "eyJhbGc...",
        "refresh_token": "eyJhbGc...",
        "token_type": "bearer",
        "expires_in": 3600
    }
    ```
    """
    try:
        result = crud.login_user(db, credentials.email, credentials.password)
        
        return schemas.TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# ============================================================
# Admin Login
# ============================================================
@router.post("/auth/admin/login", response_model=schemas.TokenResponse)
def admin_login(
    credentials: schemas.AdminLogin,
    db: Session = Depends(get_db),
):
    """
    Login an admin user and return JWT tokens.
    
    **Request:**
    ```json
    {
        "username": "admin_user",
        "password": "admin_password"
    }
    ```
    
    **Response:**
    ```json
    {
        "access_token": "eyJhbGc...",
        "refresh_token": "eyJhbGc...",
        "token_type": "bearer",
        "expires_in": 3600
    }
    ```
    """
    try:
        result = crud.login_admin(db, credentials.username, credentials.password)
        
        return schemas.TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# ============================================================
# User Registration
# ============================================================
@router.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    customer_id: int,
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new customer user.
    
    **Requirements:**
    - Customer must already exist in the system
    - Email must be unique
    - Password must be at least 6 characters
    """
    # Ensure user data has correct customer_id
    data.customer_id = customer_id
    
    try:
        # Check if customer exists
        customer = crud.get_customer(db, customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        
        # Create user
        user = crud.create_user(db, data)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# Get Current User Profile
# ============================================================
@router.get("/auth/me", response_model=schemas.UserOut)
def get_current_user_profile(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user's profile.
    
    **Headers:**
    - Authorization: Bearer <token>
    """
    from ..security import verify_token
    
    try:
        token_data = verify_token(token)
        user = crud.get_user(db, token_data.user_id)
        
        if not user or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# ============================================================
# Get Current Admin Profile
# ============================================================
@router.get("/auth/admin/me", response_model=schemas.AdminOut)
def get_current_admin_profile(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated admin's profile.
    
    **Headers:**
    - Authorization: Bearer <token>
    """
    from ..security import verify_token
    
    try:
        token_data = verify_token(token)
        admin = crud.get_admin(db, token_data.user_id)
        
        if not admin or admin.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found",
            )
        
        return admin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
