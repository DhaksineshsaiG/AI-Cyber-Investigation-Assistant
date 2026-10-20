import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.database import get_collection
from app.schemas.evidence import EvidenceResponse
from app.utils.hashing import calculate_sha256
from app.utils.sanitization import generate_evidence_id
from app.utils.storage import save_evidence_file
from app.dependencies import get_current_user, verify_case_access
from app.config import settings

router = APIRouter(prefix="/api/cases/{case_id}/evidence", tags=["Evidence"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".csv", ".json", ".log", ".chat", ".eml",
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"
}

@router.post("", response_model=List[EvidenceResponse], status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Verify caller owns case or is admin
    await verify_case_access(case_id, current_user)

    if not files:
        raise HTTPException(status_code=400, detail="No evidence files submitted")

    evidence_col = get_collection("evidence")
    uploaded_results = []
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    for f in files:
        # Sanitize extension and protect against path traversal in filenames
        clean_name = os.path.basename(f.filename or "evidence_file")
        ext = Path(clean_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}' for file '{clean_name}'. Allowed: PDF, DOCX, TXT, CSV, JSON, PNG, JPG, JPEG, TIFF, EML."
            )

        # Read content bytes
        content = await f.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail=f"File '{clean_name}' is empty (0 bytes).")
        if file_size > max_bytes:
            raise HTTPException(status_code=400, detail=f"File '{clean_name}' exceeds size limit ({settings.MAX_FILE_SIZE_MB}MB).")

        evidence_id = generate_evidence_id()
        sha256_hash = calculate_sha256(content)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Save immutably to vault
        storage_path = save_evidence_file(case_id, evidence_id, clean_name, content)

        doc = {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "original_filename": clean_name,
            "file_type": ext.lstrip('.').upper(),
            "file_size": file_size,
            "sha256_hash": sha256_hash,
            "storage_path": storage_path,
            "upload_date": now_iso,
            "status": "INGESTED",
            "extraction_method": None,
            "extracted_text": ""
        }

        await evidence_col.insert_one(doc)

        uploaded_results.append(EvidenceResponse(
            evidence_id=evidence_id,
            case_id=case_id,
            original_filename=clean_name,
            file_type=doc["file_type"],
            file_size=file_size,
            sha256_hash=sha256_hash,
            upload_date=now_iso,
            status=doc["status"],
            extraction_method=None,
            extracted_text_preview=None
        ))

    return uploaded_results

@router.get("", response_model=List[EvidenceResponse])
async def list_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Verify caller owns case or is admin
    await verify_case_access(case_id, current_user)

    evidence_col = get_collection("evidence")
    cursor = evidence_col.find({"case_id": case_id}).sort("upload_date", -1)
    docs = await cursor.to_list(length=200)

    results = []
    for d in docs:
        preview = d.get("extracted_text", "")
        preview = preview[:200] if preview else None
        results.append(EvidenceResponse(
            evidence_id=d["evidence_id"],
            case_id=d["case_id"],
            original_filename=d["original_filename"],
            file_type=d.get("file_type", "FILE"),
            file_size=d.get("file_size", 0),
            sha256_hash=d.get("sha256_hash", ""),
            upload_date=d.get("upload_date", ""),
            status=d.get("status", "INGESTED"),
            extraction_method=d.get("extraction_method"),
            extracted_text_preview=preview
        ))

    return results

@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    case_id: str,
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Verify caller owns case or is admin
    await verify_case_access(case_id, current_user)

    evidence_col = get_collection("evidence")
    ev = await evidence_col.find_one({"case_id": case_id, "evidence_id": evidence_id})
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    # Clean file from vault if present
    path = ev.get("storage_path")
    if path and os.path.exists(path):
        try:
            # Ensure path is within vault directory to prevent path traversal
            resolved_path = Path(path).resolve()
            vault_root = Path(settings.EVIDENCE_VAULT_DIR).resolve()
            if vault_root in resolved_path.parents:
                os.remove(resolved_path)
        except Exception:
            pass

    await evidence_col.delete_one({"case_id": case_id, "evidence_id": evidence_id})
    return None
