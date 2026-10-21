import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from app.database import get_collection
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.case import CaseResponse, CaseReassign
from app.schemas.audit import AuditEventsListResponse, AuditSummaryResponse
from app.dependencies import get_current_active_admin
from app.utils.security import hash_password
from app.services.audit_service import (
    record_audit_event, query_audit_events, compute_audit_summary, generate_audit_pdf_report
)

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

    # Record audit event
    await record_audit_event(
        actor_user_id=admin.get("user_id", "admin"),
        actor_role=admin.get("role", "admin"),
        action_type="user_created",
        action_label="Created a user account",
        details=f"Created account '{normalized_id}' ({doc['display_name']}) with role '{doc['role']}'",
        metadata={"target_user_id": normalized_id, "role": doc["role"]},
        status="success"
    )

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

    action_details = []
    if update_in.display_name is not None:
        updates["display_name"] = update_in.display_name.strip()
        action_details.append(f"display name updated")

    if update_in.role is not None:
        updates["role"] = update_in.role.strip().lower()
        action_details.append(f"role set to '{updates['role']}'")

    if update_in.is_active is not None:
        updates["is_active"] = update_in.is_active
        action_details.append(f"account {'activated' if update_in.is_active else 'deactivated'}")

    if update_in.password:
        updates["password_hash"] = hash_password(update_in.password)
        action_details.append("password reset")

    await users_col.update_one({"user_id": normalized_id}, {"$set": updates})
    updated_doc = await users_col.find_one({"user_id": normalized_id})

    logger.info(f"Admin '{admin.get('user_id')}' updated user account '{normalized_id}'.")

    # Record audit events
    if update_in.password:
        await record_audit_event(
            actor_user_id=admin.get("user_id", "admin"),
            actor_role=admin.get("role", "admin"),
            action_type="password_reset",
            action_label="Reset user password",
            details=f"Administrator reset password for user '{normalized_id}'",
            metadata={"target_user_id": normalized_id},
            status="success"
        )

    if update_in.is_active is not None or update_in.role is not None or update_in.display_name is not None:
        await record_audit_event(
            actor_user_id=admin.get("user_id", "admin"),
            actor_role=admin.get("role", "admin"),
            action_type="user_updated",
            action_label="Updated an account",
            details=f"Updated account '{normalized_id}': {', '.join(action_details)}",
            metadata={"target_user_id": normalized_id, "is_active": update_in.is_active},
            status="success"
        )

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

    old_owner = case.get("owner_user_id", "unassigned")
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

    # Record audit event
    await record_audit_event(
        actor_user_id=admin.get("user_id", "admin"),
        actor_role=admin.get("role", "admin"),
        action_type="investigation_reassigned",
        action_label="Transferred an investigation",
        case_id=case_id,
        details=f"Transferred investigation '{case_id}' from '@{old_owner}' to '@{target_user_id}'",
        metadata={"old_owner": old_owner, "new_owner": target_user_id},
        status="success"
    )

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


# ==============================================================================
# AUDIT LOGGING & ACTIVITY MONITOR ENDPOINTS (Admin-Only Protected)
# ==============================================================================

@router.get("/audit/events", response_model=AuditEventsListResponse)
async def get_audit_events(
    investigator_id: Optional[str] = Query(None, description="Filter by investigator user ID or 'all'"),
    action_type: Optional[str] = Query(None, description="Filter by action type or 'all'"),
    start_date: Optional[str] = Query(None, description="Start date ISO string"),
    end_date: Optional[str] = Query(None, description="End date ISO string"),
    case_id: Optional[str] = Query(None, description="Filter by investigation ID"),
    search: Optional[str] = Query(None, description="Keyword search in action and details"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    admin: dict = Depends(get_current_active_admin)
):
    """
    Returns server-recorded audit events with filtering, search, and pagination.
    Strictly restricted to administrators.
    """
    res = await query_audit_events(
        investigator_id=investigator_id,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
        case_id=case_id,
        search=search,
        page=page,
        limit=limit
    )
    return res


@router.get("/audit/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    investigator_id: Optional[str] = Query(None, description="Filter by investigator user ID or 'all'"),
    start_date: Optional[str] = Query(None, description="Start date ISO string"),
    end_date: Optional[str] = Query(None, description="End date ISO string"),
    admin: dict = Depends(get_current_active_admin)
):
    """
    Returns factual summary metric counts calculated from recorded audit events.
    Strictly restricted to administrators.
    """
    res = await compute_audit_summary(
        investigator_id=investigator_id,
        start_date=start_date,
        end_date=end_date
    )
    return res


@router.get("/audit/report/pdf")
async def download_audit_report_pdf(
    investigator_id: Optional[str] = Query(None, description="Target investigator ID or 'all'"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Start date ISO string"),
    end_date: Optional[str] = Query(None, description="End date ISO string"),
    case_id: Optional[str] = Query(None, description="Filter by investigation ID"),
    filter_label: Optional[str] = Query("All Time", description="Human-readable reporting period label"),
    admin: dict = Depends(get_current_active_admin)
):
    """
    Generates and streams a formal PDF Investigator Activity Audit Report.
    Strictly restricted to administrators.
    """
    summary = await compute_audit_summary(
        investigator_id=investigator_id,
        start_date=start_date,
        end_date=end_date
    )

    # Fetch all matching events up to 500 for the PDF report
    events_res = await query_audit_events(
        investigator_id=investigator_id,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
        case_id=case_id,
        page=1,
        limit=200
    )

    investigator_info = None
    if investigator_id and investigator_id.strip().lower() != "all":
        users_col = get_collection("users")
        investigator_info = await users_col.find_one({"user_id": investigator_id.strip().lower()})

    pdf_buffer = generate_audit_pdf_report(
        summary=summary,
        events=events_res["events"],
        investigator_info=investigator_info,
        filter_label=filter_label or "All Time"
    )

    safe_target = investigator_id.replace(" ", "_") if investigator_id else "All_Investigators"
    safe_filename = f"Investigator_Activity_Audit_Report_{safe_target}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        }
    )
