import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_collection
from app.utils.security import decode_access_token

logger = logging.getLogger("investigation.auth")
security_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> dict:
    """Extracts and verifies the JWT Bearer token from the Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    users_col = get_collection("users")
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or has been removed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact a system administrator."
        )

    return user

async def get_current_active_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Ensures caller has the 'admin' role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative privileges required."
        )
    return current_user

async def verify_case_access(case_id: str, current_user: dict) -> dict:
    """
    Verifies that the requested case exists and that the caller is authorized.
    - Admins can access all cases (including unassigned legacy cases).
    - Investigators can access ONLY cases where owner_user_id == current_user.user_id.
    """
    cases_col = get_collection("cases")
    case = await cases_col.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case '{case_id}' not found."
        )

    # Admins have full access across all cases
    if current_user.get("role") == "admin":
        return case

    # Investigators can only access cases they own
    owner = case.get("owner_user_id")
    if owner and owner == current_user.get("user_id"):
        return case

    # If the case is unassigned or owned by another user, deny access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: You do not have permission to access this case."
    )
