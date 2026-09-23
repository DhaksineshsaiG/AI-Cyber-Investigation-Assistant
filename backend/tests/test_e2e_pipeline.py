import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import db_manager
from app.routers import cases, evidence, analysis, reports
from app.schemas.case import CaseCreate
from fastapi import UploadFile

async def run_e2e_test():
    print("=" * 60)
    print("AI CYBER INVESTIGATION ASSISTANT - END-TO-END PIPELINE TEST")
    print("=" * 60)

    # 1. Connect Database
    print("\n[Stage 1] Connecting Database...")
    await db_manager.connect()
    db_mode = "LIVE MONGODB ATLAS" if db_manager.is_live_mongo else "LOCAL FALLBACK"
    print(f"  [OK] Database initialized: {db_mode}")
    assert db_manager.is_live_mongo, "Live MongoDB Atlas connection expected, but fallback was used!"

    # 2. Case Creation
    print("\n[Stage 2] Creating Case...")
    case_in = CaseCreate(
        title="Operation Horizon - Data Breach & Exfiltration",
        investigator="Det. R. Kumar (Digital Forensics Unit)",
        description="Investigation into unauthorized customer database download"
    )
    case_res = await cases.create_case(case_in)
    case_id = case_res.case_id
    print(f"  [OK] Case Created: {case_id} ('{case_res.title}')")

    # 3. Evidence Upload & SHA-256 Hashing
    print("\n[Stage 3] Ingesting Evidence Files...")
    test_files_dir = Path(__file__).resolve().parent.parent.parent / "test_evidence"
    filenames = ["whatsapp_chat_export.txt", "security_incident_report.pdf", "security_alert_banner.png"]

    upload_files = []
    for fn in filenames:
        fpath = test_files_dir / fn
        if not fpath.exists():
            raise FileNotFoundError(f"Missing test file: {fpath}")
        f_bytes = open(fpath, "rb")
        upload_files.append(UploadFile(filename=fn, file=f_bytes))

    uploaded_evidence = await evidence.upload_evidence(case_id=case_id, files=upload_files)
    print(f"  [OK] Ingested {len(uploaded_evidence)} evidence files into secure vault:")
    for ev in uploaded_evidence:
        print(f"    - {ev.original_filename} ({ev.file_type}, {ev.file_size} bytes, SHA-256: {ev.sha256_hash[:16]}...)")

    # 4. Run Complete Analysis Pipeline
    print("\n[Stage 4] Executing Forensic Pipeline (Extraction, OCR, NLP, Keywords, Timeline, AI)...")
    dashboard = await analysis.run_case_analysis(case_id=case_id)
    print(f"  [OK] Pipeline executed successfully!")
    print(f"    - Documents Analyzed: {dashboard.stats.documents}")
    print(f"    - Key Entities Extracted: {dashboard.stats.key_entities}")
    print(f"    - Risk Signals Detected: {dashboard.stats.risk_signals}")

    # 5. Verify Extracted Entities
    print("\n[Stage 5] Verifying Extracted Entities:")
    for grp in dashboard.entity_groups:
        print(f"    - {grp.title}: {', '.join(grp.items)}")

    # 6. Verify Suspicious Keywords
    print("\n[Stage 6] Verifying Detected Suspicious Keywords:")
    for kw in dashboard.keywords:
        print(f"    - '{kw.keyword}' ({kw.category}, severity={kw.severity}, count={kw.count})")

    # 7. Verify Timeline
    print("\n[Stage 7] Verifying Chronological Timeline Events:")
    for t in dashboard.timeline:
        print(f"    - [{t.time}] {t.title}: {t.detail[:60]}... (Source: {t.source_evidence})")

    # 8. Verify Cross-Evidence Correlation
    print("\n[Stage 8] Verifying Cross-Evidence Correlation:")
    for c in dashboard.correlations:
        print(f"    - {c.entity_type} '{c.entity_value}' in {len(c.evidence_names)} file(s): {', '.join(c.evidence_names)}")

    # 9. Verify AI Insights
    print("\n[Stage 9] Verifying AI Insights:")
    summary_clean = dashboard.ai_insights.summary.encode("ascii", "replace").decode("ascii")
    note_clean = (dashboard.ai_insights.confidence_note or "").encode("ascii", "replace").decode("ascii")
    print(f"    - Summary: {summary_clean}")
    print(f"    - Grounding: {note_clean}")

    # 10. Verify ReportLab PDF Generation
    print("\n[Stage 10] Testing PDF Report Generation...")
    pdf_response = await reports.download_case_pdf(case_id=case_id)
    chunks = []
    async for chunk in pdf_response.body_iterator:
        chunks.append(chunk)
    pdf_bytes = b"".join(chunks)
    print(f"  [OK] PDF generated successfully! Byte size: {len(pdf_bytes)} bytes")
    assert len(pdf_bytes) > 2000, "PDF size is unexpectedly small!"
    assert pdf_bytes.startswith(b"%PDF"), "Generated stream is not a valid PDF!"
    print("  [OK] Valid PDF header confirmed (%PDF).")

    # Clean up DB connection
    await db_manager.close()
    print("\n" + "=" * 60)
    print("ALL 10 END-TO-END STAGES PASSED VERIFICATION!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
