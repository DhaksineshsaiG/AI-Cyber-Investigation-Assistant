from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from app.database import get_collection
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse
from app.utils.sanitization import generate_case_id

router = APIRouter(prefix="/api/cases", tags=["Cases"])

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_in: CaseCreate):
    cases_col = get_collection("cases")
    case_id = generate_case_id()
    now_iso = datetime.now().isoformat()

    doc = {
        "case_id": case_id,
        "title": case_in.title.strip(),
        "investigator": case_in.investigator.strip() or "Lead Cyber Investigator",
        "description": case_in.description.strip(),
        "status": "ACTIVE",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    await cases_col.insert_one(doc)

    return CaseResponse(
        case_id=case_id,
        title=doc["title"],
        investigator=doc["investigator"],
        description=doc["description"],
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        evidence_count=0
    )

@router.get("", response_model=List[CaseResponse])
async def list_cases():
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")

    cursor = cases_col.find({})
    cases = await cursor.to_list(length=100)

    results = []
    for c in cases:
        ev_count = await evidence_col.count_documents({"case_id": c["case_id"]})
        results.append(CaseResponse(
            case_id=c["case_id"],
            title=c["title"],
            investigator=c.get("investigator", "Primary Investigator"),
            description=c.get("description", ""),
            status=c.get("status", "ACTIVE"),
            created_at=c.get("created_at", ""),
            updated_at=c.get("updated_at", ""),
            evidence_count=ev_count
        ))

    return results

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str):
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")

    c = await cases_col.find_one({"case_id": case_id})
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")

    ev_count = await evidence_col.count_documents({"case_id": case_id})
    return CaseResponse(
        case_id=c["case_id"],
        title=c["title"],
        investigator=c.get("investigator", "Primary Investigator"),
        description=c.get("description", ""),
        status=c.get("status", "ACTIVE"),
        created_at=c.get("created_at", ""),
        updated_at=c.get("updated_at", ""),
        evidence_count=ev_count
    )

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str):
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")
    analysis_col = get_collection("analysis")

    res = await cases_col.delete_one({"case_id": case_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")

    await evidence_col.delete_many({"case_id": case_id})
    await analysis_col.delete_many({"case_id": case_id})
    return None
