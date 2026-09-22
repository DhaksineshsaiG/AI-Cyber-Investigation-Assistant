import json
import logging
import re
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger("investigation.gemini")

def generate_ai_insights(
    case_id: str,
    case_title: str,
    evidence_summary_list: List[Dict[str, Any]],
    entities_grouped: Dict[str, List[str]],
    keywords_detected: List[Dict[str, Any]],
    timeline_events: List[Dict[str, Any]],
    correlations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executes grounded AI analysis via Google Gemini API.
    Returns structured assistive investigation insights.
    If API key is missing or invalid, gracefully returns availability status.
    """
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "summary": "AI assistive analysis is currently offline. Configure GEMINI_API_KEY in backend/.env to enable automated LLM evidence synthesis.",
            "findings": [
                "Deterministic forensic extraction completed (OCR, NER, and Keyword Taxonomy active).",
                "Review the extracted entities and suspicious keywords in the cards below."
            ],
            "patterns": [
                "Cross-evidence correlation active based on matching entities and keywords."
            ],
            "leads": [
                "Cross-check extracted phone numbers and email addresses against institutional records.",
                "Verify file integrity hashes against external threat intelligence repositories."
            ],
            "confidence_note": "Forensic rule-based verification active (LLM offline)",
            "is_available": False
        }

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Prepare sanitized evidence context
        evidence_context = {
            "case_id": case_id,
            "case_title": case_title,
            "evidence_files": [
                {
                    "name": ev.get("filename"),
                    "size_bytes": ev.get("size"),
                    "sha256": ev.get("sha256"),
                    "text_snippet": (ev.get("text") or "")[:2000]
                }
                for ev in evidence_summary_list
            ],
            "extracted_entities": {k: v[:15] for k, v in entities_grouped.items() if v},
            "suspicious_keywords": [
                {"keyword": kw["keyword"], "category": kw["category"], "severity": kw["severity"], "count": kw["count"]}
                for kw in keywords_detected[:12]
            ],
            "timeline": [
                {"time": ev["time"], "title": ev["title"], "detail": ev["detail"], "source": ev["source_evidence"]}
                for ev in timeline_events[:10]
            ],
            "correlations": [
                {"entity": c["entity_value"], "type": c["entity_type"], "sources": c["evidence_names"]}
                for c in correlations[:8]
            ]
        }

        system_instruction = (
            "You are an expert digital forensics and cybercrime investigation assistant. "
            "Analyze the provided structured evidence strictly based on the extracted facts. "
            "CRITICAL RULES:\n"
            "1. Do NOT invent, assume, or fabricate any facts, names, dates, or files not present in the evidence.\n"
            "2. Ground every insight in the provided evidence and cite specific filenames or entities where relevant.\n"
            "3. Clearly identify leads as investigative hypotheses for verification, not confirmed conclusions.\n"
            "4. Respond ONLY with a valid JSON object matching the following structure:\n"
            "{\n"
            '  "summary": "Concise 2-3 sentence overview of the evidence findings",\n'
            '  "findings": ["Specific observation 1 citing evidence source", "Specific observation 2"],\n'
            '  "patterns": ["Identified behavioral or technical pattern 1"],\n'
            '  "leads": ["Actionable lead for the investigator to follow up"],\n'
            '  "confidence_note": "Methodological basis of analysis (e.g. Grounded on 3 correlated sources)"\n'
            "}"
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"EVIDENCE DOSSIER:\n{json.dumps(evidence_context, indent=2)}\n\n"
            "Provide the JSON analysis now:"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw_text = response.text.strip()
        # Clean markdown codeblocks if enclosed
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        parsed = json.loads(raw_text)
        return {
            "summary": parsed.get("summary", "Analysis completed."),
            "findings": parsed.get("findings", []),
            "patterns": parsed.get("patterns", []),
            "leads": parsed.get("leads", []),
            "confidence_note": parsed.get("confidence_note", "Grounded on extracted evidence"),
            "is_available": True
        }

    except Exception as e:
        logger.error(f"Gemini API analysis failed: {e}")
        return {
            "summary": f"AI analysis encountered an error: {str(e)[:100]}. Rule-based extraction remains valid.",
            "findings": ["Evidence extracted successfully; LLM synthesis unavailable."],
            "patterns": [],
            "leads": ["Continue manual review of timeline and extracted entities."],
            "confidence_note": "Rule-based analysis",
            "is_available": False
        }
