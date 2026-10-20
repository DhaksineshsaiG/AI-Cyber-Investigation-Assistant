import shutil
from pathlib import Path
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from app.config import settings
from app.database import get_collection
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.utils.sanitization import generate_case_id
from app.dependencies import get_current_user, get_current_active_admin, verify_case_access

router = APIRouter(prefix="/api/cases", tags=["Cases"])

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_in: CaseCreate,
    current_user: dict = Depends(get_current_user)
):
    cases_col = get_collection("cases")
    case_id = generate_case_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    owner_id = current_user["user_id"]
    display_name = current_user.get("display_name") or owner_id

    doc = {
        "case_id": case_id,
        "title": case_in.title.strip(),
        "owner_user_id": owner_id,
        "investigator": display_name,
        "description": case_in.description.strip(),
        "status": "ACTIVE",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    await cases_col.insert_one(doc)

    return CaseResponse(
        case_id=case_id,
        title=doc["title"],
        owner_user_id=owner_id,
        investigator=doc["investigator"],
        description=doc["description"],
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        evidence_count=0
    )

@router.get("", response_model=List[CaseResponse])
async def list_cases(current_user: dict = Depends(get_current_user)):
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")

    # Admin can view all cases; Investigators can view ONLY cases they own
    if current_user.get("role") == "admin":
        filter_query = {}
    else:
        filter_query = {"owner_user_id": current_user["user_id"]}

    cursor = cases_col.find(filter_query).sort("created_at", -1)
    cases = await cursor.to_list(length=200)

    results = []
    for c in cases:
        ev_count = await evidence_col.count_documents({"case_id": c["case_id"]})
        results.append(CaseResponse(
            case_id=c["case_id"],
            title=c["title"],
            owner_user_id=c.get("owner_user_id"),
            investigator=c.get("investigator", "Primary Investigator"),
            description=c.get("description", ""),
            status=c.get("status", "ACTIVE"),
            created_at=c.get("created_at", ""),
            updated_at=c.get("updated_at", ""),
            evidence_count=ev_count
        ))

    return results

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user: dict = Depends(get_current_user)
):
    case = await verify_case_access(case_id, current_user)
    evidence_col = get_collection("evidence")

    ev_count = await evidence_col.count_documents({"case_id": case_id})
    return CaseResponse(
        case_id=case["case_id"],
        title=case["title"],
        owner_user_id=case.get("owner_user_id"),
        investigator=case.get("investigator", "Primary Investigator"),
        description=case.get("description", ""),
        status=case.get("status", "ACTIVE"),
        created_at=case.get("created_at", ""),
        updated_at=case.get("updated_at", ""),
        evidence_count=ev_count
    )

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    admin: dict = Depends(get_current_active_admin)
):
    # Restricted strictly to system administrators for chain-of-custody preservation
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")
    analysis_col = get_collection("analysis")

    res = await cases_col.delete_one({"case_id": case_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    await evidence_col.delete_many({"case_id": case_id})
    await analysis_col.delete_many({"case_id": case_id})

    # Clean up disk vault folder if present
    vault_path = Path(settings.EVIDENCE_VAULT_DIR) / case_id
    if vault_path.exists() and vault_path.is_dir():
        try:
            shutil.rmtree(vault_path, ignore_errors=True)
        except Exception:
            pass

    return None
