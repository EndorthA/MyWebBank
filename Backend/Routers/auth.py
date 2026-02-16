# Backend/Routers/auth.py
"""
Authentication endpoints for users and admins.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from .. import crud, schemas
from ..crud import AuthError, NotFoundError
from ..security import verify_token, TokenData


router = APIRouter(tags=["auth"])


# ============================================================
# Helper: Extract token from Authorization header
# ============================================================

def extract_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return authorization.split(" ", 1)[1]


# ============================================================
# Current User/Admin Dependencies
# ============================================================

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> TokenData:
    """
    Get the current authenticated user from the token.
    Can be used as a dependency in route handlers.
    
    Usage:
        @router.get("/me")
        def get_profile(current_user: TokenData = Depends(get_current_user)):
            return current_user
    """
    token = extract_token_from_header(authorization)
    
    try:
        token_data = verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if token_data.user_type != "user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type",
        )
    
    user = crud.get_user(db, token_data.user_id)
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or is deleted",
        )
    
    return token_data


def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> TokenData:
    """
    Get the current authenticated admin from the token.
    Can be used as a dependency in route handlers.
    
    Usage:
        @router.get("/admin/stats")
        def get_stats(current_admin: TokenData = Depends(get_current_admin)):
            return {...}
    """
    token = extract_token_from_header(authorization)
    
    try:
        token_data = verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type - admin access required",
        )
    
    admin = crud.get_admin(db, token_data.user_id)
    if not admin or admin.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or is deleted",
        )
    
    return token_data


# ============================================================
# Role-Based Access Control (RBAC) Dependencies
# ============================================================

def require_role(*allowed_roles: str):
    """
    Create a dependency that checks if the current user has one of the allowed roles.
    
    Usage:
        @router.delete("/accounts/{account_id}")
        def delete_account(
            account_id: int,
            current_user: TokenData = Depends(require_role("customer")),
        ):
            return {...}
    """
    def check_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user
    
    return check_role


def require_admin_role(*allowed_roles: str):
    """
    Create a dependency that checks if the current admin has one of the allowed roles.
    
    Usage:
        @router.post("/admins")
        def create_admin(
            data: schemas.AdminCreate,
            current_admin: TokenData = Depends(require_admin_role("super_admin"))
        ):
            return {...}
    """
    def check_role(current_admin: TokenData = Depends(get_current_admin)) -> TokenData:
        if current_admin.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return current_admin
    
    return check_role


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[TokenData]:
    """
    Get the current user if authenticated, otherwise return None.
    Useful for endpoints that work with or without authentication.
    
    Usage:
        @router.get("/public-data")
        def get_data(current_user: Optional[TokenData] = Depends(get_optional_user)):
            if current_user:
                return {...}
            else:
                return {...}
    """
    if not authorization:
        return None
    
    try:
        token = extract_token_from_header(authorization)
        token_data = verify_token(token)
        if token_data.user_type == "user":
            user = crud.get_user(db, token_data.user_id)
            if user and not user.is_deleted:
                return token_data
    except ValueError:
        pass
    
    return None


# ============================================================
# Login / Register / Profile Endpoints
# ============================================================


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
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user's profile.
    
    **Headers:**
    - Authorization: Bearer <token>
    """
    from ..security import verify_token
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    try:
        token = authorization.split(" ", 1)[1]
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
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated admin's profile.
    
    **Headers:**
    - Authorization: Bearer <token>
    """
    from ..security import verify_token
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    try:
        token = authorization.split(" ", 1)[1]
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
