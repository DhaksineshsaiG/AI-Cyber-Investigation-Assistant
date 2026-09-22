from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class EntityGroup(BaseModel):
    title: str
    category: str
    tone: str
    items: List[str]

class KeywordItem(BaseModel):
    keyword: str
    category: str
    severity: str
    count: int
    snippets: List[str]

class TimelineItem(BaseModel):
    time: str
    date_iso: Optional[str] = None
    title: str
    detail: str
    color: str
    source_evidence: str
    has_location: bool = False

class CorrelationItem(BaseModel):
    entity_type: str
    entity_value: str
    evidence_names: List[str]
    occurrences: int

class AIInsightData(BaseModel):
    summary: str
    findings: List[str]
    patterns: List[str]
    leads: List[str]
    confidence_note: str
    is_available: bool

class DashboardStats(BaseModel):
    documents: int
    key_entities: int
    risk_signals: int

class DashboardResponse(BaseModel):
    case_id: str
    title: str
    investigator: str
    status: str
    evidence_count: int
    stats: DashboardStats
    summary: str
    sources_reviewed_label: str
    keywords: List[KeywordItem]
    entity_groups: List[EntityGroup]
    timeline: List[TimelineItem]
    correlations: List[CorrelationItem]
    ai_insights: AIInsightData
