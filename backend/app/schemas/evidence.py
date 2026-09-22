from pydantic import BaseModel
from typing import Optional

class EvidenceResponse(BaseModel):
    evidence_id: str
    case_id: str
    original_filename: str
    file_type: str
    file_size: int
    sha256_hash: str
    upload_date: str
    status: str
    extraction_method: Optional[str] = None
    extracted_text_preview: Optional[str] = None
