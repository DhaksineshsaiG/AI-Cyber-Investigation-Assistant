from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AuditEventResponse(BaseModel):
    event_id: str
    timestamp: str
    actor_user_id: str
    actor_role: str
    action_type: str
    action_label: str
    case_id: Optional[str] = None
    details: str = ""
    status: str = "success"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AuditEventsListResponse(BaseModel):
    events: List[AuditEventResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int

class AuditSummaryResponse(BaseModel):
    total_activities: int
    investigations_created: int
    evidence_uploaded: int
    analysis_runs: int
    reports_downloaded: int
    account_changes: int
    failed_operations: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    investigator_id: str = "all"
