export interface CaseItem {
  case_id: string;
  title: string;
  investigator: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  evidence_count: number;
}

export interface EvidenceItem {
  evidence_id: string;
  case_id: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  sha256_hash: string;
  upload_date: string;
  status: string;
  extraction_method?: string | null;
  extracted_text_preview?: string | null;
}

export interface EntityGroupItem {
  title: string;
  category: string;
  tone: string;
  items: string[];
}

export interface KeywordMatch {
  keyword: string;
  category: string;
  severity: string;
  count: number;
  snippets: string[];
}

export interface TimelineNode {
  time: string;
  date_iso?: string | null;
  title: string;
  detail: string;
  color: string;
  source_evidence: string;
  has_location?: boolean;
}

export interface CorrelationNode {
  entity_type: string;
  entity_value: string;
  evidence_names: string[];
  occurrences: number;
  description?: string;
}

export interface AIInsights {
  summary: string;
  findings: string[];
  patterns: string[];
  leads: string[];
  confidence_note: string;
  is_available: boolean;
}

export interface DashboardData {
  case_id: string;
  title: string;
  investigator: string;
  status: string;
  evidence_count: number;
  stats: {
    documents: number;
    key_entities: number;
    risk_signals: number;
  };
  summary: string;
  sources_reviewed_label: string;
  keywords: KeywordMatch[];
  entity_groups: EntityGroupItem[];
  timeline: TimelineNode[];
  correlations: CorrelationNode[];
  ai_insights: AIInsights;
}
