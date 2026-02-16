# Backend/auth.py
"""
Authentication and Authorization dependencies for FastAPI.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .security import verify_token, TokenData
from . import crud, models


# ============================================================
# Current User/Admin Dependencies
# ============================================================

def get_current_user(
    token: str = None,
    db: Session = Depends(get_db),
) -> TokenData:
    """
    Get the current authenticated user from the token.
    Can be used as a dependency in route handlers.
    
    Usage:
        @router.get("/me")
        def get_current_user(current_user: TokenData = Depends(get_current_user)):
            return current_user
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    token: str = None,
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
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
            current_admin: TokenData = Depends(require_role("super_admin"))
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


# ============================================================
# Optional Current User (doesn't fail if not authenticated)
# ============================================================

def get_optional_user(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Optional[TokenData]:
    """
    Get the current user if authenticated, otherwise return None.
    Useful for endpoints that work with or without authentication.
    
    Usage:
        @router.get("/public-data")
        def get_data(current_user: Optional[TokenData] = Depends(get_optional_user)):
            if current_user:
                # User-specific data
                return {...}
            else:
                # Public data
                return {...}
    """
    if not token:
        return None
    
    try:
        token_data = verify_token(token)
        if token_data.user_type == "user":
            user = crud.get_user(db, token_data.user_id)
            if user and not user.is_deleted:
                return token_data
    except ValueError:
        pass
    
    return None
