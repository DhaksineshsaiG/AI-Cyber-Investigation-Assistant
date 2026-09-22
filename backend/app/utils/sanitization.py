import re
import uuid
from datetime import datetime

def sanitize_filename(filename: str) -> str:
    """Removes path traversal characters and unsafe filesystem symbols."""
    # Keep only alphanumeric, dots, underscores, and dashes
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    clean_name = clean_name.strip('._')
    return clean_name or "evidence_file"

def generate_case_id(prefix: str = "CASE") -> str:
    """Generates a professional forensic Case ID, e.g. CASE-2026-A8F3"""
    year = datetime.now().year
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"{prefix}-{year}-{short_uuid}"

def generate_evidence_id(prefix: str = "EVID") -> str:
    """Generates a unique Evidence ID, e.g. EVID-7B29C"""
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{short_uuid}"
