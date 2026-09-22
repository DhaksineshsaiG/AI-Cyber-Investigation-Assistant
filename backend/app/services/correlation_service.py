from typing import List, Dict, Any
from collections import defaultdict

def correlate_cross_evidence(evidence_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyzes multiple evidence files to uncover common entities, matching contacts,
    shared IP addresses, and overlapping keywords across separate sources.
    """
    if len(evidence_items) < 1:
        return []

    entity_to_sources = defaultdict(lambda: {"sources": set(), "count": 0, "type": "UNKNOWN"})

    for ev in evidence_items:
        source_name = ev.get("filename", "Evidence")
        entities = ev.get("entities", [])
        keywords = ev.get("keywords", [])

        # Track entities
        for ent in entities:
            val = ent.get("value", "").strip()
            ent_type = ent.get("type", "ENTITY")
            if val and len(val) > 2:
                key = (ent_type, val)
                entity_to_sources[key]["sources"].add(source_name)
                entity_to_sources[key]["count"] += 1
                entity_to_sources[key]["type"] = ent_type

        # Track high-risk keywords
        for kw in keywords:
            w = kw.get("keyword", "").strip()
            if w and kw.get("severity") == "high":
                key = ("SUSPICIOUS_KEYWORD", w)
                entity_to_sources[key]["sources"].add(source_name)
                entity_to_sources[key]["count"] += kw.get("count", 1)
                entity_to_sources[key]["type"] = "KEYWORD"

    correlations = []

    # Prioritize items found in multiple files, but if single file, include top entities
    for (ent_type, val), data in entity_to_sources.items():
        source_list = sorted(list(data["sources"]))
        # Items that span across 2 or more evidence files are high-value cross-correlations
        if len(source_list) >= 2 or len(evidence_items) == 1:
            correlations.append({
                "entity_type": ent_type,
                "entity_value": val,
                "evidence_names": source_list,
                "occurrences": data["count"],
                "description": f"Observed in {len(source_list)} source(s): {', '.join(source_list)}"
            })

    # Sort: multi-file correlations first, then by occurrence count
    correlations.sort(key=lambda x: (len(x["evidence_names"]), x["occurrences"]), reverse=True)
    return correlations[:10]
