from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CaseCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150, description="Title of the cyber investigation case")
    investigator: str = Field(default="Primary Investigator", max_length=100)
    description: Optional[str] = Field(default="", max_length=1000)

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    investigator: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class CaseResponse(BaseModel):
    case_id: str
    title: str
    investigator: str
    description: str
    status: str
    created_at: str
    updated_at: str
    evidence_count: int = 0
