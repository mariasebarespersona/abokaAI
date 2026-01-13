"""
Authentication Middleware for FastAPI using Supabase Auth.

This module provides JWT verification for protecting API endpoints.
"""

import os
import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # Public anon key for auth verification
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # Optional: for local JWT verification

# Security scheme
security = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Represents an authenticated user from Supabase."""
    
    def __init__(self, id: str, email: str, role: str = "authenticated", metadata: dict = None):
        self.id = id
        self.email = email
        self.role = role
        self.metadata = metadata or {}
    
    def __repr__(self):
        return f"AuthenticatedUser(id={self.id}, email={self.email})"


async def verify_supabase_token(token: str) -> Optional[AuthenticatedUser]:
    """
    Verify a Supabase JWT token and return the user.
    
    Uses Supabase's /auth/v1/user endpoint to verify the token
    and get user information.
    """
    if not SUPABASE_URL:
        logger.error("[AUTH] SUPABASE_URL not configured")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_ANON_KEY or ""
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return AuthenticatedUser(
                    id=user_data.get("id"),
                    email=user_data.get("email"),
                    role=user_data.get("role", "authenticated"),
                    metadata=user_data.get("user_metadata", {})
                )
            else:
                logger.warning(f"[AUTH] Token verification failed: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"[AUTH] Error verifying token: {e}")
        return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/api/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    # Check for token in Authorization header
    if credentials:
        token = credentials.credentials
        user = await verify_supabase_token(token)
        if user:
            return user
    
    # Check for token in cookie (for SSR/browser requests)
    token_from_cookie = request.cookies.get("sb-access-token")
    if token_from_cookie:
        user = await verify_supabase_token(token_from_cookie)
        if user:
            return user
    
    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Please provide a valid access token.",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if not authenticated (doesn't raise exception).
    
    Usage:
        @app.get("/api/public")
        async def public_route(user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous"}
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_owner(resource_user_id: str, current_user: AuthenticatedUser) -> bool:
    """
    Check if the current user owns the resource.
    
    Usage:
        if not require_owner(property.user_id, user):
            raise HTTPException(403, "Not authorized to access this resource")
    """
    if current_user.id != resource_user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this resource"
        )
    return True

