import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, status, Depends
from app.database import get_collection
from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse, BootstrapRequest
from app.schemas.user import UserResponse
from app.dependencies import get_current_user
from app.utils.security import (
    hash_password, verify_password, create_access_token, login_rate_limiter
)
from app.services.audit_service import record_audit_event

logger = logging.getLogger("investigation.auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    normalized_id = req.user_id.strip().lower()
    
    # Check brute-force rate limiter
    login_rate_limiter.check_rate_limit(normalized_id)

    users_col = get_collection("users")
    user = await users_col.find_one({"user_id": normalized_id})

    # Generic authentication error to avoid user enumeration
    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid user ID or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user:
        login_rate_limiter.record_failure(normalized_id)
        await record_audit_event(
            actor_user_id=normalized_id,
            actor_role="anonymous",
            action_type="login_failure",
            action_label="Failed sign in attempt",
            details="Invalid user ID or password provided",
            status="failure"
        )
        raise generic_error

    # Verify password hash
    if not verify_password(req.password, user.get("password_hash", "")):
        login_rate_limiter.record_failure(normalized_id)
        await record_audit_event(
            actor_user_id=normalized_id,
            actor_role=user.get("role", "investigator"),
            action_type="login_failure",
            action_label="Failed sign in attempt",
            details="Invalid password provided for registered user",
            status="failure"
        )
        raise generic_error

    # Verify active status
    if not user.get("is_active", True):
        await record_audit_event(
            actor_user_id=normalized_id,
            actor_role=user.get("role", "investigator"),
            action_type="login_failure",
            action_label="Failed sign in attempt",
            details="Sign in attempted on deactivated account",
            status="failure"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator."
        )

    # Success: reset rate limiter
    login_rate_limiter.record_success(normalized_id)

    # Update last login timestamp
    now_iso = datetime.now(timezone.utc).isoformat()
    await users_col.update_one(
        {"user_id": normalized_id},
        {"$set": {"last_login_at": now_iso}}
    )

    token = create_access_token({
        "sub": user["user_id"],
        "role": user["role"],
        "display_name": user.get("display_name", user["user_id"])
    })

    # Record successful login event
    await record_audit_event(
        actor_user_id=user["user_id"],
        actor_role=user["role"],
        action_type="login_success",
        action_label="Signed in",
        details="User successfully signed in to workspace",
        status="success"
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            user_id=user["user_id"],
            display_name=user.get("display_name", user["user_id"]),
            role=user["role"],
            is_active=user.get("is_active", True),
            created_at=user.get("created_at", now_iso),
            updated_at=user.get("updated_at", now_iso),
            last_login_at=now_iso,
            created_by=user.get("created_by")
        )
    )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Stateless JWT logout: The client clears the access token locally.
    Server logs the intentional logout event without exposing secrets.
    """
    logger.info(f"User '{current_user.get('user_id')}' logged out.")
    await record_audit_event(
        actor_user_id=current_user["user_id"],
        actor_role=current_user.get("role", "investigator"),
        action_type="logout",
        action_label="Signed out",
        details="User initiated workspace sign out",
        status="success"
    )
    return {"detail": "Logged out successfully."}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user["user_id"],
        display_name=current_user.get("display_name", current_user["user_id"]),
        role=current_user["role"],
        is_active=current_user.get("is_active", True),
        created_at=current_user.get("created_at", ""),
        updated_at=current_user.get("updated_at", ""),
        last_login_at=current_user.get("last_login_at"),
        created_by=current_user.get("created_by")
    )

@router.post("/bootstrap", response_model=TokenResponse)
async def bootstrap_initial_admin(
    req: BootstrapRequest,
    x_bootstrap_key: str = Header(default="", alias="X-Bootstrap-Key")
):
    """
    One-time initial bootstrap endpoint.
    Only allows creating an administrator if exactly ZERO admin accounts currently exist in the database.
    If BOOTSTRAP_SECRET_KEY is configured in server environment, requires matching key.
    """
    users_col = get_collection("users")
    admin_count = await users_col.count_documents({"role": "admin"})

    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System already initialized. An administrator account already exists. Please log in as an administrator."
        )

    # If server has BOOTSTRAP_SECRET_KEY configured, verify it
    server_key = (settings.BOOTSTRAP_SECRET_KEY or "").strip()
    if server_key:
        provided_key = (req.bootstrap_key or x_bootstrap_key or "").strip()
        if provided_key != server_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid bootstrap secret key."
            )

    normalized_id = req.user_id.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(req.password)

    user_doc = {
        "user_id": normalized_id,
        "display_name": req.display_name.strip() or "System Administrator",
        "password_hash": password_hash,
        "role": "admin",
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_login_at": now_iso,
        "created_by": "bootstrap"
    }

    await users_col.insert_one(user_doc)
    logger.info(f"System successfully bootstrapped with initial admin: '{normalized_id}'.")

    token = create_access_token({
        "sub": normalized_id,
        "role": "admin",
        "display_name": user_doc["display_name"]
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            user_id=normalized_id,
            display_name=user_doc["display_name"],
            role="admin",
            is_active=True,
            created_at=now_iso,
            updated_at=now_iso,
            last_login_at=now_iso,
            created_by="bootstrap"
        )
    )
