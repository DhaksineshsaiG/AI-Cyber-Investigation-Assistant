import os
from pathlib import Path
from app.config import settings
from app.utils.sanitization import sanitize_filename

def get_case_vault_path(case_id: str) -> Path:
    """Returns directory path for a specific case's evidence vault."""
    vault_dir = Path(settings.EVIDENCE_VAULT_DIR) / case_id
    vault_dir.mkdir(parents=True, exist_ok=True)
    return vault_dir

def save_evidence_file(case_id: str, evidence_id: str, original_filename: str, file_bytes: bytes) -> str:
    """Saves raw evidence immutably into the case vault."""
    vault_dir = get_case_vault_path(case_id)
    safe_name = sanitize_filename(original_filename)
    dest_filename = f"{evidence_id}_{safe_name}"
    dest_path = vault_dir / dest_filename

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return str(dest_path.resolve())
