import io
import os
import sys
from pathlib import Path
import httpx
from pypdf import PdfReader

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def run_production_e2e_verification():
    print("=" * 70)
    print("PRODUCTION POST-DEPLOYMENT COMPREHENSIVE VERIFICATION")
    print("=" * 70)

    vercel_url = "https://ai-cyber-investigation-assistant.vercel.app"
    backend_url = "https://ai-cyber-investigation-assistant.onrender.com"

    client = httpx.Client(timeout=120.0, follow_redirects=True)

    # 1. Health check & CORS
    print("\n[Step 1] Verifying Live Backend Health & CORS Preflight...")
    health_res = client.get(f"{backend_url}/api/health")
    assert health_res.status_code == 200, f"Backend returned {health_res.status_code}"
    health = health_res.json()
    print(f"  [OK] Backend Health: {health}")
    assert health.get("status") == "healthy", "Backend not healthy"
    assert "Atlas" in health.get("database", ""), "Backend not connected to Atlas"
    assert health.get("groq_configured") is True, "Groq not configured"

    cors_res = client.options(
        f"{backend_url}/api/health",
        headers={
            "Origin": vercel_url,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert cors_res.status_code == 200, f"CORS preflight failed: {cors_res.status_code}"
    allowed_origin = cors_res.headers.get("access-control-allow-origin")
    print(f"  [OK] CORS Preflight Passed: Access-Control-Allow-Origin: {allowed_origin}")
    assert allowed_origin == vercel_url or allowed_origin == "*", "CORS origin mismatch"

    # 2. Vercel Website check
    print(f"\n[Step 2] Verifying Vercel Production Website ({vercel_url})...")
    v_res = client.get(vercel_url)
    assert v_res.status_code == 200, f"Vercel returned {v_res.status_code}"
    assert "<title>" in v_res.text, "Vercel HTML missing <title>"
    print(f"  [OK] Vercel Website 200 OK (HTML: {len(v_res.text)} bytes)")

    # 3. Create fresh test case
    print("\n[Step 3] Creating Fresh Production Test Case...")
    case_title = "Operation Horizon - Production Verification Dossier"
    investigator = "Lead Inspector S. Vance (DFIR Unit)"
    description = "Automated post-deployment verification of digital evidence intelligence pipeline."
    case_res = client.post(
        f"{backend_url}/api/cases",
        json={
            "title": case_title,
            "investigator": investigator,
            "description": description
        }
    )
    assert case_res.status_code in (200, 201), f"Create case failed: {case_res.text}"
    case_data = case_res.json()
    case_id = case_data["case_id"]
    print(f"  [OK] Case Created on Live Atlas: {case_id}")

    try:
        # 4. Upload evidence files
        print("\n[Step 4] Uploading Multi-Format Evidence Files to Vault...")
        test_dir = Path(__file__).resolve().parent.parent.parent / "test_evidence"
        files_to_upload = [
            ("files", ("whatsapp_chat_export.txt", open(test_dir / "whatsapp_chat_export.txt", "rb"), "text/plain")),
            ("files", ("security_incident_report.pdf", open(test_dir / "security_incident_report.pdf", "rb"), "application/pdf")),
            ("files", ("security_alert_banner.png", open(test_dir / "security_alert_banner.png", "rb"), "image/png")),
        ]
        upload_res = client.post(f"{backend_url}/api/cases/{case_id}/evidence", files=files_to_upload)
        assert upload_res.status_code in (200, 201), f"Evidence upload failed: {upload_res.text}"
        evidence_list = upload_res.json()
        print(f"  [OK] Successfully Ingested {len(evidence_list)} Evidence Files:")
        evidence_hashes = {}
        for ev in evidence_list:
            evidence_hashes[ev["original_filename"]] = ev["sha256_hash"]
            print(f"       - {ev['original_filename']} ({ev['file_type']}, {ev['file_size']} B, SHA-256: {ev['sha256_hash'][:16]}...)")

        # 5. Run full forensic pipeline
        print("\n[Step 5] Triggering End-to-End Forensic Analysis with Live Groq Synthesis...")
        analyze_res = client.post(f"{backend_url}/api/cases/{case_id}/analyze")
        assert analyze_res.status_code == 200, f"Analysis failed: {analyze_res.text}"
        dashboard = analyze_res.json()

        # 6. Verify dashboard contents
        print("\n[Step 6] Verifying Live Analysis Output:")
        stats = dashboard.get("stats", {})
        print(f"  [OK] Documents Analyzed: {stats.get('documents')}")
        print(f"  [OK] Key Entities Extracted: {stats.get('key_entities')}")
        print(f"  [OK] Risk Signals Detected: {stats.get('risk_signals')}")
        assert stats.get("documents") == 3, f"Expected 3 documents, got {stats.get('documents')}"
        assert stats.get("key_entities") >= 10, "Too few entities extracted"

        # Check Entities
        entity_groups = dashboard.get("entity_groups", [])
        extracted_names = []
        for g in entity_groups:
            if g.get("category") == "Names":
                extracted_names = g.get("items", [])
        print(f"  [OK] Names Identified: {', '.join(extracted_names)}")
        assert any("Vance" in n for n in extracted_names) or any("Elena" in n for n in extracted_names), "Expected suspect names not found"

        # Check Suspicious Keywords
        keywords = dashboard.get("keywords", [])
        kw_names = [k["keyword"] for k in keywords]
        print(f"  [OK] Suspicious Keywords Detected: {', '.join(kw_names[:6])}...")
        assert any(k in kw_names for k in ["wipe", "unauthorized", "exfiltration", "admin override"]), "Critical keywords missing"

        # Check Timeline
        timeline = dashboard.get("timeline", [])
        print(f"  [OK] Timeline Milestones Generated: {len(timeline)} events")
        assert len(timeline) >= 4, "Too few timeline events extracted"

        # Check Correlations
        correlations = dashboard.get("correlations", [])
        print(f"  [OK] Cross-Evidence Correlations: {len(correlations)} linkages")
        for c in correlations[:3]:
            print(f"       * {c['entity_type']} '{c['entity_value']}' in {len(c['evidence_names'])} files: {', '.join(c['evidence_names'])}")
        assert len(correlations) >= 1, "Expected cross-evidence correlations"

        # Check Groq AI Insights
        ai = dashboard.get("ai_insights", {})
        assert ai.get("is_available") is True, "AI insights is not marked available"
        summary_text = ai.get("summary", "")
        clean_summary = summary_text.encode("ascii", "replace").decode("ascii")
        print(f"  [OK] Live Groq AI Summary: {clean_summary[:140]}...")
        assert len(summary_text) > 20, "AI summary too brief"
        assert len(ai.get("findings", [])) > 0, "No key findings generated"
        assert len(ai.get("leads", [])) > 0, "No follow-up leads generated"

        # 7. Verify exported PDF report
        print("\n[Step 7] Exporting and Auditing Forensic PDF Dossier...")
        pdf_res = client.get(f"{backend_url}/api/cases/{case_id}/report/pdf")
        assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.status_code}"
        pdf_bytes = pdf_res.content
        print(f"  [OK] PDF Downloaded: {len(pdf_bytes)} bytes")
        assert pdf_bytes.startswith(b"%PDF"), "Response is not a valid PDF file"
        assert len(pdf_bytes) > 5000, "PDF size is suspiciously small"

        # Read and inspect PDF text with pypdf
        reader = PdfReader(io.BytesIO(pdf_bytes))
        print(f"  [OK] PDF Total Pages: {len(reader.pages)}")
        assert len(reader.pages) >= 2, "Expected multi-page forensic dossier"

        pdf_full_text = ""
        for page in reader.pages:
            pdf_full_text += page.extract_text() or ""

        # Validate that PDF includes case-specific data
        assert case_id in pdf_full_text, f"Case ID {case_id} missing from PDF!"
        print(f"  [OK] Confirmed Case ID '{case_id}' in PDF text.")
        assert "S. Vance" in pdf_full_text or "DFIR" in pdf_full_text, "Investigator name missing from PDF!"
        print("  [OK] Confirmed Investigator Name in PDF text.")

        # Check SHA-256 hashes in PDF
        for fname, fhash in evidence_hashes.items():
            # Monospace SHA-256 might be formatted with space or split lines
            first_half = fhash[:32]
            second_half = fhash[32:]
            assert (first_half in pdf_full_text) or (fhash in pdf_full_text), f"SHA-256 hash for {fname} missing from PDF!"
            print(f"  [OK] Confirmed SHA-256 hash for '{fname}' in PDF text.")

        # Check AI insights summary in PDF
        # First 30 chars of summary should be in PDF
        summary_snippet = summary_text[:30].strip()
        assert summary_snippet in pdf_full_text, "AI summary missing from PDF!"
        print(f"  [OK] Confirmed Live AI Synthesis in PDF text ('{summary_snippet}...').")

        print("\n" + "=" * 70)
        print("ALL 7 PRODUCTION POST-DEPLOYMENT VERIFICATION STEPS PASSED (100%)!")
        print("=" * 70)

    finally:
        # Cleanup
        print(f"\n[Cleanup] Deleting test case {case_id} from live production Atlas...")
        del_res = client.delete(f"{backend_url}/api/cases/{case_id}")
        print(f"  [OK] Cleaned up case {case_id} (Status {del_res.status_code})")

if __name__ == "__main__":
    run_production_e2e_verification()
