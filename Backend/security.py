# Backend/security.py
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import os
from typing import Optional, Union

import jwt
from pydantic import BaseModel


# ============================================================
# Configuration
# ============================================================

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ============================================================
# Token Schemas
# ============================================================

class TokenData(BaseModel):
    """Data contained in JWT token."""
    user_id: int
    user_type: str  # "user" or "admin"
    role: str
    email_or_username: str
    

class Token(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


# ============================================================
# Password hashing (PBKDF2 - stdlib only)
# ============================================================

_PBKDF2_ITERS = 200_000


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return f"pbkdf2${_PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against its hash."""
    try:
        scheme, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False

        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)

        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ============================================================
# JWT Token Management
# ============================================================

def create_access_token(
    user_id: int,
    user_type: str,  # "user" or "admin"
    role: str,
    email_or_username: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: ID of the user/admin
        user_type: Type of user ("user" for customer or "admin" for admin)
        role: Role of the user (e.g., "customer", "admin", "super_admin")
        email_or_username: Email for users, username for admins
        expires_delta: Custom expiration time. If None, uses default.
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "role": role,
        "email_or_username": email_or_username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: int,
    user_type: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: ID of the user/admin
        user_type: Type of user ("user" for customer or "admin" for admin)
        expires_delta: Custom expiration time. If None, uses default (7 days).
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData with decoded information
    
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify it's an access token
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        
        user_id = payload.get("user_id")
        user_type = payload.get("user_type")
        role = payload.get("role")
        email_or_username = payload.get("email_or_username")
        
        if not all([user_id, user_type, role, email_or_username]):
            raise ValueError("Invalid token payload")
        
        return TokenData(
            user_id=user_id,
            user_type=user_type,
            role=role,
            email_or_username=email_or_username,
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def verify_refresh_token(token: str) -> tuple:
    """
    Verify and decode a JWT refresh token.
    
    Args:
        token: JWT token string
    
    Returns:
        Tuple of (user_id, user_type)
    
    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        user_id = payload.get("user_id")
        user_type = payload.get("user_type")
        
        if not all([user_id, user_type]):
            raise ValueError("Invalid token payload")
        
        return (user_id, user_type)
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


# ============================================================
# Backwards compatibility (deprecated)
# ============================================================

def create_access_token_legacy(user_id: int, expires_minutes: int = 60) -> str:
    """DEPRECATED: Use create_access_token instead."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    nonce = secrets.token_urlsafe(24)
    return f"devtoken.user={user_id}.exp={int(exp.timestamp())}.{nonce}"


def parse_token_legacy(token: str) -> int:
    """DEPRECATED: Use verify_token instead."""
    try:
        parts = token.split(".")
        user_id = int(parts[0].split("user=")[1])
        exp_ts = int(parts[1].split("exp=")[1])

        if datetime.now(timezone.utc).timestamp() > exp_ts:
            raise ValueError("Token expired")

        return user_id
    except Exception:
        raise ValueError("Invalid token")