import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from app.database import get_collection
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.case import CaseResponse, CaseReassign
from app.dependencies import get_current_active_admin
from app.utils.security import hash_password

logger = logging.getLogger("investigation.admin")
router = APIRouter(prefix="/api/admin", tags=["Admin Management"])

@router.get("/users", response_model=List[UserResponse])
async def list_users(admin: dict = Depends(get_current_active_admin)):
    users_col = get_collection("users")
    cursor = users_col.find({}).sort("created_at", -1)
    docs = await cursor.to_list(length=200)

    results = []
    for d in docs:
        results.append(UserResponse(
            user_id=d["user_id"],
            display_name=d.get("display_name", d["user_id"]),
            role=d.get("role", "investigator"),
            is_active=d.get("is_active", True),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            last_login_at=d.get("last_login_at"),
            created_by=d.get("created_by")
        ))
    return results

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    admin: dict = Depends(get_current_active_admin)
):
    users_col = get_collection("users")
    normalized_id = user_in.user_id.strip().lower()

    existing = await users_col.find_one({"user_id": normalized_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID '{normalized_id}' is already registered."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(user_in.password)

    doc = {
        "user_id": normalized_id,
        "display_name": user_in.display_name.strip(),
        "password_hash": password_hash,
        "role": user_in.role.strip().lower(),
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_login_at": None,
        "created_by": admin.get("user_id", "admin")
    }

    await users_col.insert_one(doc)
    logger.info(f"Admin '{admin.get('user_id')}' created new user '{normalized_id}' with role '{doc['role']}'.")

    return UserResponse(
        user_id=doc["user_id"],
        display_name=doc["display_name"],
        role=doc["role"],
        is_active=doc["is_active"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        last_login_at=None,
        created_by=doc["created_by"]
    )

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_in: UserUpdate,
    admin: dict = Depends(get_current_active_admin)
):
    normalized_id = user_id.strip().lower()
    users_col = get_collection("users")

    target = await users_col.find_one({"user_id": normalized_id})
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User account '{normalized_id}' not found."
        )

    # Security check: Prevent disabling or removing the last active administrator
    is_target_admin = target.get("role") == "admin"
    is_disabling = update_in.is_active is False
    is_demoting = update_in.role is not None and update_in.role != "admin"

    if is_target_admin and (is_disabling or is_demoting):
        active_admin_count = await users_col.count_documents({"role": "admin", "is_active": True})
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security policy violation: Cannot deactivate or demote the last active system administrator."
            )

    updates = {}
    now_iso = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now_iso

    if update_in.display_name is not None:
        updates["display_name"] = update_in.display_name.strip()

    if update_in.role is not None:
        updates["role"] = update_in.role.strip().lower()

    if update_in.is_active is not None:
        updates["is_active"] = update_in.is_active

    if update_in.password:
        updates["password_hash"] = hash_password(update_in.password)

    await users_col.update_one({"user_id": normalized_id}, {"$set": updates})
    updated_doc = await users_col.find_one({"user_id": normalized_id})

    logger.info(f"Admin '{admin.get('user_id')}' updated user account '{normalized_id}'.")

    return UserResponse(
        user_id=updated_doc["user_id"],
        display_name=updated_doc.get("display_name", updated_doc["user_id"]),
        role=updated_doc["role"],
        is_active=updated_doc.get("is_active", True),
        created_at=updated_doc.get("created_at", ""),
        updated_at=updated_doc.get("updated_at", ""),
        last_login_at=updated_doc.get("last_login_at"),
        created_by=updated_doc.get("created_by")
    )

@router.patch("/cases/{case_id}/reassign", response_model=CaseResponse)
async def reassign_case_owner(
    case_id: str,
    reassign_in: CaseReassign,
    admin: dict = Depends(get_current_active_admin)
):
    cases_col = get_collection("cases")
    users_col = get_collection("users")
    evidence_col = get_collection("evidence")

    case = await cases_col.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found."
        )

    target_user_id = reassign_in.owner_user_id.strip().lower()
    target_user = await users_col.find_one({"user_id": target_user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user '{target_user_id}' not found."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    await cases_col.update_one(
        {"case_id": case_id},
        {"$set": {
            "owner_user_id": target_user_id,
            "investigator": target_user.get("display_name", target_user_id),
            "updated_at": now_iso
        }}
    )

    ev_count = await evidence_col.count_documents({"case_id": case_id})
    updated_case = await cases_col.find_one({"case_id": case_id})

    logger.info(f"Case '{case_id}' reassigned to '{target_user_id}' by admin '{admin.get('user_id')}'.")

    return CaseResponse(
        case_id=updated_case["case_id"],
        title=updated_case["title"],
        owner_user_id=updated_case.get("owner_user_id"),
        investigator=updated_case.get("investigator", target_user_id),
        description=updated_case.get("description", ""),
        status=updated_case.get("status", "ACTIVE"),
        created_at=updated_case.get("created_at", ""),
        updated_at=updated_case.get("updated_at", ""),
        evidence_count=ev_count
    )
