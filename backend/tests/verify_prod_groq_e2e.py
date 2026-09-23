import httpx
import os
import sys

def test_prod_groq_pipeline():
    base_url = "https://ai-cyber-investigation-assistant.onrender.com"
    client = httpx.Client(base_url=base_url, timeout=90.0)

    print("=" * 60)
    print("PRODUCTION GROQ AI PIPELINE VERIFICATION")
    print("=" * 60)

    # 1. Health check
    print("\n[Step 1] Checking Live Backend Health...")
    health = client.get("/api/health").json()
    print(f"  [OK] Health: {health}")
    assert health.get("groq_configured") is True, "Groq is not configured on production backend!"

    # 2. Create a clean test case
    print("\n[Step 2] Creating Production Test Case...")
    case_res = client.post("/api/cases", json={
        "title": "Live Production AI Forensics Verification",
        "investigator": "Automated Deployment Verifier",
        "description": "Verification of Groq AI synthesis in production"
    })
    assert case_res.status_code in (200, 201), f"Failed to create case: {case_res.text}"
    case_data = case_res.json()
    case_id = case_data["case_id"]
    print(f"  [OK] Case Created: {case_id}")

    try:
        # 3. Upload evidence files
        print("\n[Step 3] Uploading Evidence Files...")
        test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_evidence")
        files_to_upload = [
            ("files", ("whatsapp_chat_export.txt", open(os.path.join(test_dir, "whatsapp_chat_export.txt"), "rb"), "text/plain")),
            ("files", ("security_incident_report.pdf", open(os.path.join(test_dir, "security_incident_report.pdf"), "rb"), "application/pdf")),
        ]
        upload_res = client.post(f"/api/cases/{case_id}/evidence", files=files_to_upload)
        assert upload_res.status_code in (200, 201), f"Upload failed: {upload_res.text}"
        evidence_list = upload_res.json()
        print(f"  [OK] Uploaded {len(evidence_list)} evidence files")

        # 4. Trigger Analysis
        print("\n[Step 4] Running Forensic Analysis with Live Groq Synthesis...")
        analyze_res = client.post(f"/api/cases/{case_id}/analyze")
        assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
        dashboard = analyze_res.json()

        # 5. Verify Groq AI Insights
        print("\n[Step 5] Inspecting AI Insights Output:")
        ai = dashboard.get("ai_insights", {})
        is_avail = ai.get("is_available")
        summary = ai.get("summary", "")
        findings = ai.get("findings", [])
        leads = ai.get("leads", [])
        conf = ai.get("confidence_note", "")

        print(f"  [OK] is_available: {is_avail}")
        print(f"  [OK] AI Summary: {summary[:160].encode('ascii', 'replace').decode('ascii')}...")
        print(f"  [OK] Key Findings Count: {len(findings)}")
        for f in findings[:2]:
            print(f"       * {f.encode('ascii', 'replace').decode('ascii')}")
        print(f"  [OK] Leads Count: {len(leads)}")
        for l in leads[:2]:
            print(f"       * {l.encode('ascii', 'replace').decode('ascii')}")
        print(f"  [OK] Confidence Note: {conf.encode('ascii', 'replace').decode('ascii')}")

        assert is_avail is True, f"AI insights is_available is False! Summary: {summary}"
        assert len(summary) > 20, "Summary too short!"
        assert len(findings) > 0, "No findings generated!"
        print("\n[SUCCESS] Production Groq AI Synthesis Verified Successfully!")

    finally:
        # 6. Cleanup
        print("\n[Step 6] Cleaning up test case...")
        del_res = client.delete(f"/api/cases/{case_id}")
        print(f"  [OK] Cleaned up case {case_id} (Status {del_res.status_code})")

    print("\n" + "=" * 60)
    print("ALL PRODUCTION GROQ AI TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_prod_groq_pipeline()
