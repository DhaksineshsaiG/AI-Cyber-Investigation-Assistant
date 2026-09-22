import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil import parser as date_parser

logger = logging.getLogger("investigation.timeline")

# Regex to detect date/time patterns in lines of evidence text
TIMESTAMP_LINE_PATTERNS = [
    # ISO timestamps: 2026-06-14 09:42[:00] or 2026-06-14T09:42:00
    re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)'),
    # Standard format: 14 Jun 2026 09:42 or 14/06/2026, 09:42
    re.compile(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}(?:[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)?)', re.IGNORECASE),
    # US format: Jun 14, 2026 09:42 AM
    re.compile(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}(?:[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)?)', re.IGNORECASE),
    # Slash dates: 2026/06/14 09:42 or 14/06/2026 09:42
    re.compile(r'(\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\s+\d{1,2}:\d{2}(?::\d{2})?)')
]

HIGH_RISK_TERMS = ["breach", "unauthorized", "unrecognized", "wipe", "delete", "stolen", "exfiltration", "malware", "shadow", "leak", "exploit"]
MEDIUM_RISK_TERMS = ["transfer", "shared", "external", "vendor", "export", "login", "modified", "download"]

def extract_timeline_events(text: str, evidence_name: str) -> List[Dict[str, Any]]:
    """
    Extracts chronological timeline events from evidence text.
    Never invents timestamps; events are only generated when temporal data is explicitly present.
    """
    if not text:
        return []

    events = []
    lines = text.split("\n")

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line or len(cleaned_line) < 5:
            continue

        matched_dt_str = None
        for pattern in TIMESTAMP_LINE_PATTERNS:
            match = pattern.search(cleaned_line)
            if match:
                matched_dt_str = match.group(1).strip()
                break

        if matched_dt_str:
            parsed_dt = None
            try:
                # Parse date string safely
                parsed_dt = date_parser.parse(matched_dt_str, fuzzy=True)
            except Exception:
                continue

            if not parsed_dt:
                continue

            # Strip the timestamp itself from the text line to get the descriptive detail
            event_detail = cleaned_line.replace(matched_dt_str, "").strip(" -:[](),\t")
            if not event_detail:
                event_detail = "Activity recorded in evidence log."

            # Determine title & risk
            lower_detail = event_detail.lower()
            if any(term in lower_detail for term in HIGH_RISK_TERMS):
                color = "bg-rose-500"
                risk_level = "high"
                title = "Suspicious Security Event"
            elif any(term in lower_detail for term in MEDIUM_RISK_TERMS):
                color = "bg-amber-500"
                risk_level = "medium"
                title = "Evidence Activity Recorded"
            else:
                color = "bg-sky-500"
                risk_level = "low"
                title = "Communication / System Event"

            # Check if mentions an IP, city, or login location
            has_location = bool(re.search(r'\b(?:location|ip|address|login from|origin|server|terminal)\b', lower_detail))

            # Format human readable time: e.g. "14 Jun · 09:42" or "14 Jun 2026 · 09:42"
            formatted_time = parsed_dt.strftime("%d %b · %H:%M")

            events.append({
                "event_id": f"EVT-{uuid.uuid4().hex[:6].upper()}",
                "raw_timestamp": parsed_dt,
                "date_iso": parsed_dt.isoformat(),
                "time": formatted_time,
                "title": title,
                "detail": event_detail,
                "color": color,
                "risk_level": risk_level,
                "source_evidence": evidence_name,
                "has_location": has_location
            })

    # Sort strictly chronologically by parsed timestamp
    events.sort(key=lambda x: x["raw_timestamp"])

    # Clean raw_timestamp before returning
    for e in events:
        del e["raw_timestamp"]

    return events
