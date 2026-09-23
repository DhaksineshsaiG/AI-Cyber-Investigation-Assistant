import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.database import get_collection
from app.schemas.analysis import (
    DashboardResponse, DashboardStats, EntityGroup, KeywordItem,
    TimelineItem, CorrelationItem, AIInsightData
)
from app.processors.text_extractor import extract_text_from_file
from app.services.nlp_service import extract_entities_from_text
from app.services.keyword_service import detect_suspicious_keywords
from app.services.timeline_service import extract_timeline_events
from app.services.correlation_service import correlate_cross_evidence
from app.services.groq_service import generate_ai_insights

logger = logging.getLogger("investigation.analysis")
router = APIRouter(prefix="/api/cases/{case_id}", tags=["Analysis"])

@router.post("/analyze", response_model=DashboardResponse)
async def run_case_analysis(case_id: str):
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")
    analysis_col = get_collection("analysis")

    case = await cases_col.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    evidence_cursor = evidence_col.find({"case_id": case_id})
    evidence_docs = await evidence_cursor.to_list(length=100)

    if not evidence_docs:
        raise HTTPException(status_code=400, detail="Cannot analyze case with zero evidence files.")

    all_evidence_items = []
    combined_entities_map = {
        "Names": set(),
        "Dates": set(),
        "Phone Numbers": set(),
        "Email Addresses": set(),
        "IP & System Addresses": set(),
        "Organizations": set()
    }
    all_keywords_list = []
    all_timeline_events = []

    # Process each evidence file
    for ev in evidence_docs:
        path = ev.get("storage_path", "")
        filename = ev.get("original_filename", "Evidence")
        
        # 1. Text Extraction / OCR (reuse persisted text if file path is unavailable across container restarts)
        extracted_text = ""
        extraction_method = ev.get("extraction_method", "Direct Text Stream")
        if path and os.path.exists(path):
            ext_res = extract_text_from_file(path, filename)
            extracted_text = ext_res["extracted_text"]
            extraction_method = ext_res["extraction_method"]
        elif ev.get("extracted_text"):
            extracted_text = ev["extracted_text"]
            extraction_method = ev.get("extraction_method", "Persisted Forensic Text")
        elif path:
            ext_res = extract_text_from_file(path, filename)
            extracted_text = ext_res["extracted_text"]
            extraction_method = ext_res["extraction_method"]
        
        # Update evidence document in DB
        await evidence_col.update_one(
            {"evidence_id": ev["evidence_id"]},
            {"$set": {
                "extracted_text": extracted_text,
                "extraction_method": extraction_method,
                "status": "ANALYZED"
            }}
        )

        # 2. NLP Entity Extraction
        nlp_res = extract_entities_from_text(extracted_text, filename)
        for cat, items in nlp_res["grouped"].items():
            if cat in combined_entities_map:
                combined_entities_map[cat].update(items)

        # 3. Suspicious Keyword Detection
        kw_res = detect_suspicious_keywords(extracted_text, filename)
        all_keywords_list.extend(kw_res)

        # 4. Timeline Events
        time_res = extract_timeline_events(extracted_text, filename)
        all_timeline_events.extend(time_res)

        all_evidence_items.append({
            "evidence_id": ev["evidence_id"],
            "filename": filename,
            "size": ev.get("file_size", 0),
            "sha256": ev.get("sha256_hash", ""),
            "text": extracted_text,
            "entities": nlp_res["all_entities"],
            "keywords": kw_res,
            "timeline": time_res
        })

    # Deduplicate and sort keywords
    kw_agg = {}
    for kw in all_keywords_list:
        key = kw["keyword"].lower()
        if key not in kw_agg:
            kw_agg[key] = {
                "keyword": kw["keyword"],
                "category": kw["category"],
                "severity": kw["severity"],
                "count": 0,
                "snippets": []
            }
        kw_agg[key]["count"] += kw["count"]
        for s in kw.get("snippets", []):
            if len(kw_agg[key]["snippets"]) < 3 and s not in kw_agg[key]["snippets"]:
                kw_agg[key]["snippets"].append(s)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_keywords = sorted(list(kw_agg.values()), key=lambda x: (severity_order.get(x["severity"], 3), -x["count"]))

    # Sort all timeline events chronologically
    sorted_timeline = sorted(all_timeline_events, key=lambda x: x.get("date_iso") or "")

    # 5. Cross-Evidence Correlation
    correlations = correlate_cross_evidence(all_evidence_items)

    # Convert entities map to EntityGroup list matching UI
    tones = {
        "Names": "bg-sky-50 text-sky-700",
        "Dates": "bg-violet-50 text-violet-700",
        "Phone Numbers": "bg-emerald-50 text-emerald-700",
        "Email Addresses": "bg-amber-50 text-amber-700",
        "IP & System Addresses": "bg-rose-50 text-rose-700",
        "Organizations": "bg-indigo-50 text-indigo-700"
    }

    entity_groups = []
    total_entities = 0
    for cat, items in combined_entities_map.items():
        sorted_items = sorted(list(items))
        if sorted_items:
            entity_groups.append(EntityGroup(
                title=cat,
                category=cat,
                tone=tones.get(cat, "bg-slate-50 text-slate-700"),
                items=sorted_items
            ))
            total_entities += len(sorted_items)

    # 6. Groq AI Investigation Insights
    ai_insights_res = generate_ai_insights(
        case_id=case_id,
        case_title=case.get("title", ""),
        evidence_summary_list=all_evidence_items,
        entities_grouped={k: list(v) for k, v in combined_entities_map.items()},
        keywords_detected=sorted_keywords,
        timeline_events=sorted_timeline,
        correlations=correlations
    )

    # Calculate metrics
    risk_signals_count = sum(1 for kw in sorted_keywords if kw["severity"] == "high") + sum(1 for ev in sorted_timeline if ev["risk_level"] == "high")

    # Generate dynamic investigation summary
    doc_count = len(evidence_docs)
    summary_text = (
        f"Forensic ingestion of {doc_count} evidence file(s) across case {case_id} yielded "
        f"{total_entities} verified entity marker(s) and {len(sorted_keywords)} risk taxonomy indicator(s). "
    )
    if correlations:
        top_corr = correlations[0]
        summary_text += f"Key cross-evidence linkage: '{top_corr['entity_value']}' detected across {len(top_corr['evidence_names'])} evidence sources."
    elif sorted_keywords:
        top_kw = sorted_keywords[0]
        summary_text += f"Primary security indicator: '{top_kw['keyword']}' ({top_kw['category']}) with {top_kw['count']} hit(s)."
    else:
        summary_text += "No high-risk exfiltration or wiping signatures immediately surfaced in the extracted records."

    dashboard_data = {
        "case_id": case_id,
        "title": case.get("title", "Investigation Case"),
        "investigator": case.get("investigator", "Primary Investigator"),
        "status": case.get("status", "ACTIVE"),
        "evidence_count": doc_count,
        "stats": {
            "documents": doc_count,
            "key_entities": total_entities,
            "risk_signals": risk_signals_count
        },
        "summary": summary_text,
        "sources_reviewed_label": f"{doc_count} source{'s' if doc_count != 1 else ''} reviewed",
        "keywords": sorted_keywords,
        "entity_groups": [g.model_dump() for g in entity_groups],
        "timeline": sorted_timeline,
        "correlations": correlations,
        "ai_insights": ai_insights_res
    }

    # Persist in DB
    await analysis_col.update_one(
        {"case_id": case_id},
        {"$set": dashboard_data},
        upsert=True
    )

    return DashboardResponse(
        case_id=dashboard_data["case_id"],
        title=dashboard_data["title"],
        investigator=dashboard_data["investigator"],
        status=dashboard_data["status"],
        evidence_count=dashboard_data["evidence_count"],
        stats=DashboardStats(**dashboard_data["stats"]),
        summary=dashboard_data["summary"],
        sources_reviewed_label=dashboard_data["sources_reviewed_label"],
        keywords=[KeywordItem(**kw) for kw in dashboard_data["keywords"]],
        entity_groups=[EntityGroup(**eg) for eg in dashboard_data["entity_groups"]],
        timeline=[TimelineItem(**t) for t in dashboard_data["timeline"]],
        correlations=[CorrelationItem(**c) for c in dashboard_data["correlations"]],
        ai_insights=AIInsightData(**dashboard_data["ai_insights"])
    )

@router.get("/dashboard", response_model=DashboardResponse)
async def get_case_dashboard(case_id: str):
    cases_col = get_collection("cases")
    analysis_col = get_collection("analysis")
    evidence_col = get_collection("evidence")

    case = await cases_col.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cached_analysis = await analysis_col.find_one({"case_id": case_id})
    if cached_analysis:
        # If cached analysis had Groq offline but Groq is now configured and evidence exists,
        # dynamically re-run analysis to generate and persist real AI insights
        cached_ai = cached_analysis.get("ai_insights", {})
        groq_ready = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip() != "your_groq_api_key_here")
        ev_count = await evidence_col.count_documents({"case_id": case_id})
        if not cached_ai.get("is_available", False) and groq_ready and ev_count > 0:
            logger.info(f"Cached analysis for case {case_id} had AI offline. Re-running synthesis with active Groq service...")
            try:
                return await run_case_analysis(case_id)
            except Exception as e:
                logger.warning(f"Auto-refreshing AI analysis failed ({e}); serving existing cached analysis.")

        return DashboardResponse(
            case_id=cached_analysis["case_id"],
            title=cached_analysis["title"],
            investigator=cached_analysis.get("investigator", case.get("investigator", "")),
            status=cached_analysis.get("status", "ACTIVE"),
            evidence_count=cached_analysis.get("evidence_count", 0),
            stats=DashboardStats(**cached_analysis["stats"]),
            summary=cached_analysis["summary"],
            sources_reviewed_label=cached_analysis["sources_reviewed_label"],
            keywords=[KeywordItem(**kw) for kw in cached_analysis.get("keywords", [])],
            entity_groups=[EntityGroup(**eg) for eg in cached_analysis.get("entity_groups", [])],
            timeline=[TimelineItem(**t) for t in cached_analysis.get("timeline", [])],
            correlations=[CorrelationItem(**c) for c in cached_analysis.get("correlations", [])],
            ai_insights=AIInsightData(**cached_analysis.get("ai_insights", {}))
        )

    # If no analysis yet, check if evidence exists
    ev_count = await evidence_col.count_documents({"case_id": case_id})
    if ev_count > 0:
        return await run_case_analysis(case_id)

    # Empty initial state
    return DashboardResponse(
        case_id=case_id,
        title=case.get("title", ""),
        investigator=case.get("investigator", "Primary Investigator"),
        status=case.get("status", "ACTIVE"),
        evidence_count=0,
        stats=DashboardStats(documents=0, key_entities=0, risk_signals=0),
        summary="Awaiting digital evidence upload. Add files to begin automated forensic analysis.",
        sources_reviewed_label="0 sources reviewed",
        keywords=[],
        entity_groups=[],
        timeline=[],
        correlations=[],
        ai_insights=AIInsightData(
            summary="No evidence uploaded yet.",
            findings=[],
            patterns=[],
            leads=[],
            confidence_note="Awaiting data",
            is_available=False
        )
    )
